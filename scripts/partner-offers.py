#!/usr/bin/env python3
"""Partner offers for useandlike.com/deals/ (Kevin, 1 Nov 2026: "strange that we have only 7 deals listed ... when we
have like 1000s of partners"). The Studio's deal tracker reads the brands' offer lists on our partner network (Yazing)
around the clock; this script takes the current ones, drops what isn't a real or current offer, and writes
data/partner-offers.json. build-pages.js shows them under the hand-checked deals (data/deals.json), labelled as the
brand's own listing on our partner network with the day we saw it there.

    python3 scripts/partner-offers.py            # run by the daily news run (NEWS.md step 4), then build-pages.js

Left out: seasonal offers out of season (Halloween in November, "Back to School", "Spring" ...), offers naming an
earlier year, lines that aren't offers ("Request a free demo", slogans), superlatives (our pages never say "best"),
lines that undercut offers (free alternative, cancel, refund), FlexOffers links (How To Rocket only), direct-link brands
(Synthesia), paused or ended links, brands without a short link, and brands that already have a hand-checked deal.
One offer per brand: a % off first, then a code, a "was/now" price, a free trial or free months.
Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID (the Studio's database); without them the file stays as it is.
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "partner-offers.json")
STUDIO_DB = "8209584b-6109-45f6-9367-5befe0f080a5"   # D1 "useandlike-studio" (useandlike-ops/studio/wrangler.toml)

BANNED = re.compile(r"\b(best|cheapest|fastest|#1|number one|top-rated|unbeatable|perfect)\b", re.I)   # as check.js
UNDERCUT = re.compile(r"\b(free shopping|for free|free alternative|premium free|license key|trial reset|cancel|"
                      r"refund|delete|unsubscribe)\b", re.I)                                          # as build-pages.js
OFFER = re.compile(r"\d+\s?%|\$\s?\d+(\.\d+)?\s?off|\bsave (up to )?[\$£€]\s?\d|\bwas:?\s?[\$£€]\s?[\d.]+.*\bnow:?\s?[\$£€]|"
                   r"\bfree trial\b|\btry (it )?free\b|\b\d+\s?(days?|weeks?|months?) free\b|\bfree for \d+\s?(days?|weeks?|months?)\b|"
                   r"\bfirst (month|year) (free|for [\$£€])|\bcash ?back\b|\bfree shipping\b|\bbogo\b|\bbuy one,? get one\b", re.I)
NOT_OFFER = re.compile(r"\b(request a (free )?demo|book a (free )?(class|call|demo|consultation)|sign up for|subscribe to|"
                       r"newsletter|join (our|the)|learn more|download (the|our) app)\b", re.I)
YEAR = re.compile(r"\b(20[12]\d)\b")


def seasonal_ok(text, today):
    """False for a seasonal offer outside its season (the network's lists keep old ones)."""
    m, d = today.month, today.day
    t = text.lower()
    seasons = [
        (r"hallowe+n|trick or treat|spooky", m == 10),
        (r"back[- ]to[- ]school", m in (7, 8, 9)),
        (r"\bspring\b", m in (3, 4, 5)),
        (r"\bsummer\b", m in (6, 7, 8)),
        (r"\b(fall|autumn)\b", m in (9, 10, 11)),
        (r"\bwinter\b", m in (12, 1, 2)),
        (r"prime (big deal )?days?", m in (7, 10)),
        (r"black friday|cyber (monday|week)", m == 11 or (m == 12 and d <= 3)),
        (r"christmas|xmas|holiday sale|holiday deal", (m == 11 and d >= 15) or m == 12),
        (r"new year", (m == 12 and d >= 26) or (m == 1 and d <= 15)),
        (r"valentine", m == 2 and d <= 14),
        (r"easter", m in (3, 4)),
        (r"mother'?s day", (m == 4 and d >= 15) or (m == 5 and d <= 15)),
        (r"father'?s day", m == 6),
        (r"labou?r day", (m == 8 and d >= 25) or (m == 9 and d <= 10)),
        (r"memorial day", m == 5),
        (r"(4th|fourth) of july|independence day", (m == 6 and d >= 20) or (m == 7 and d <= 5)),
        (r"singles'? day|11\.11|double eleven", m == 11 and d <= 11),
        (r"tax (day|season)", m in (1, 2, 3, 4)),
    ]
    for pattern, in_season in seasons:
        if re.search(pattern, t) and not in_season:
            return False
    years = [int(y) for y in YEAR.findall(text)]
    return not any(y < today.year for y in years)


def clean(text):
    t = re.sub(r"\s+", " ", text).strip().rstrip(".").strip()
    t = re.sub(r"\s*\|\s*", " · ", t)
    return t if len(t) <= 120 else t[:117].rsplit(" ", 1)[0] + "…"


def rank(o):
    """Which of a brand's offers to show: the biggest % off, then a code, then a was/now price, then the rest."""
    t = o["text"]
    return (-(o["size"] or 0), 0 if o["code"] else 1, 0 if re.search(r"\bwas\b", t, re.I) else 1, len(t))


def d1(sql, params=None):
    url = "https://api.cloudflare.com/client/v4/accounts/%s/d1/database/%s/query" % (os.environ["CLOUDFLARE_ACCOUNT_ID"], STUDIO_DB)
    req = urllib.request.Request(url, json.dumps({"sql": sql, "params": params or []}).encode(),
                                 {"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"], "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))["result"][0]["results"]
        except (urllib.error.HTTPError, urllib.error.URLError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def redirect_slugs():
    slugs = set()
    for line in open(os.path.join(ROOT, "_redirects"), encoding="utf-8"):
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("/") and not line.lstrip().startswith("#"):
            slugs.add(parts[0][1:])
    return slugs


def main():
    if not (os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID")):
        print("No Cloudflare login in this session: partner offers not refreshed (the page keeps the last list).")
        return
    today = datetime.datetime.now(datetime.timezone.utc).date()
    links = json.load(open(os.path.join(ROOT, "data", "short-links.json"), encoding="utf-8"))
    checked = {d["slug"] for d in json.load(open(os.path.join(ROOT, "data", "deals.json"), encoding="utf-8"))["deals"]}
    slugs = redirect_slugs()
    rows = d1("""SELECT d.slug, p.name, d.text, d.code, d.size, substr(d.last_seen, 1, 10) AS seen
        FROM deals d JOIN deal_programs p ON p.slug = d.slug
        WHERE d.gone IS NULL AND d.source = 'yazing' AND p.active = 1 AND d.last_seen >= datetime('now', '-3 days')""")
    why = {}
    best = {}
    for r in rows:
        slug, link = r["slug"], links.get(r["slug"]) or {}
        text = r["text"] or ""
        reason = (
            "no short link" if slug not in slugs else
            "FlexOffers (How To Rocket only)" if link.get("only") or "flexoffers" in str(link.get("source", "")).lower() else
            "direct-link brand" if link.get("direct") else
            "paused" if link.get("paused") or link.get("source") == "Left Yazing" else
            "has a checked deal" if slug in checked else
            "out of season or old" if not seasonal_ok(text, today) else
            "superlative" if BANNED.search(text) else
            "undercuts" if UNDERCUT.search(text) else
            "not an offer" if NOT_OFFER.search(text) or not (OFFER.search(text) or r["code"]) else
            None)
        if reason:
            why[reason] = why.get(reason, 0) + 1
            continue
        o = {"slug": slug, "brand": link.get("name") or r["name"], "group": link.get("group") or "More",
             "text": clean(text), "code": (r["code"] or "").strip() or None, "size": r["size"] or 0, "seen": r["seen"]}
        if link.get("countries") and link["countries"] not in ("worldwide", "?"):
            o["where"] = link["countries"]
        if slug not in best or rank(o) < rank(best[slug]):
            best[slug] = o
    offers = sorted(best.values(), key=lambda o: (o["group"].lower(), -o["size"], o["brand"].lower()))
    for o in offers:
        o.pop("size", None)
    json.dump({"_about": "Written by scripts/partner-offers.py from the Studio's deal tracker (the brands' offer lists on our "
                         "partner network, Yazing). Don't edit by hand: the next daily run rewrites it. Hand-checked deals "
                         "live in data/deals.json.",
               "updated": today.isoformat(), "offers": offers},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(OUT, "a", encoding="utf-8").write("\n")
    print("Partner offers: %d brands from %d listed offers (left out: %s)." % (
        len(offers), len(rows), ", ".join("%s %d" % kv for kv in sorted(why.items(), key=lambda kv: -kv[1])) or "none"))


if __name__ == "__main__":
    main()
