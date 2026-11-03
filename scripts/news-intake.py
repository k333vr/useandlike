#!/usr/bin/env python3
"""The day's story candidates for useandlike.com/news: the Studio's (studio.useandlike.com) rated stories from the last
days that aren't on the site yet. The daily news run reads them, checks each source and writes data/news/<slug>.json
(see NEWS.md).

    python3 scripts/news-intake.py todo [--days 3]   # JSON list, best first
    python3 scripts/news-intake.py done              # which Studio stories are on the site (item ids from data/news)
    python3 scripts/news-intake.py more              # a waiting "more stories" request from the script page, if any
    python3 scripts/news-intake.py more --done N     # mark it done (N = how many full stories went up for it)
    python3 scripts/news-intake.py rising [--days 7] # new apps climbing the App Store charts, by category (roundups)

A candidate is a story the morning AI marked "News: story" (Kevin, 1 Nov 2026: "basically no limit and also a lot of
newcomer apps") or "News: rumor" (a rumor, leak or feature in testing: Kevin wants those too, framed as such; "rumor": true),
or one it marked for the newsletter or scored 60+, unless it wrote "Skip". "News: quick" (Kevin, 3 Nov: big apps "should
only be shown if its a top story") is the smaller news of a big app: a one-liner ("quick": true in the list). Each comes
with the other outlets that reported the same news ("also"), so a fact can be checked in a second source.
Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID (the Studio's database is Cloudflare D1 "useandlike-studio").
"""
import glob, json, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ID = "8209584b-6109-45f6-9367-5befe0f080a5"   # D1 "useandlike-studio" (useandlike-ops/studio/wrangler.toml)


def query(sql, params=None):
    for k in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        if not os.environ.get(k):
            sys.exit("%s is not set." % k)
    url = "https://api.cloudflare.com/client/v4/accounts/%s/d1/database/%s/query" % (os.environ["CLOUDFLARE_ACCOUNT_ID"], DB_ID)
    req = urllib.request.Request(url, json.dumps({"sql": sql, "params": params or []}).encode(),
                                 {"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"], "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))["result"][0]["results"]
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if attempt == 3:
                detail = e.read().decode()[:300] if isinstance(e, urllib.error.HTTPError) else str(e)
                sys.exit("Database error: %s" % detail)
            time.sleep(2 ** attempt)


def on_site():
    """Studio item ids and source links of the stories already on the site."""
    items, urls = set(), set()
    for f in glob.glob(os.path.join(ROOT, "data", "news", "*.json")):
        s = json.load(open(f, encoding="utf-8"))
        for i in [s.get("item")] + list(s.get("items") or []):
            if isinstance(i, int):
                items.add(i)
        for x in s.get("sources") or []:
            if x.get("url"):
                urls.add(norm(x["url"]))
    return items, urls


def norm(u):
    return re.sub(r"^https?://(www\.)?", "", u.split("#")[0].split("?")[0]).rstrip("/").lower()


def todo(days):
    items, urls = on_site()
    rows = query("""SELECT i.id, i.title, i.url, COALESCE(i.publisher, s.name) AS source, s.grp AS grp, i.snippet,
          i.published, i.sources_count, i.ai_summary AS summary, i.ai_why AS why, i.ai_use AS use, i.ai_score AS score
        FROM items i JOIN sources s ON s.id = i.source_id
        WHERE i.cluster_id IS NULL AND i.ai_at IS NOT NULL AND i.status != 'skipped'
          AND i.published >= datetime('now', ?)
          AND (i.ai_use LIKE '%News: story%' OR i.ai_use LIKE '%News: rumor%' OR i.ai_use LIKE '%News: quick%'
               OR i.ai_use LIKE '%Newsletter:%' OR i.ai_score >= 60)
          AND COALESCE(i.ai_use, '') NOT LIKE 'Skip%'
        ORDER BY (i.ai_use LIKE '%News: story%' OR i.ai_use LIKE '%News: rumor%') DESC, (i.ai_use LIKE '%News: quick%') DESC,
          i.ai_score DESC, i.sources_count DESC""", ["-%d days" % days])
    rows = [r for r in rows if r["id"] not in items and norm(r["url"]) not in urls]
    if rows:
        ids = ",".join(str(r["id"]) for r in rows)
        also = {}
        for a in query("""SELECT i.cluster_id AS c, COALESCE(i.publisher, s.name) AS source, i.title, i.url
                FROM items i JOIN sources s ON s.id = i.source_id WHERE i.cluster_id IN (%s) ORDER BY i.published""" % ids):
            # Google News links are redirects that often don't open: the direct ones first.
            also.setdefault(a.pop("c"), []).append(a)
        for r in rows:
            r["also"] = sorted(also.get(r["id"], []), key=lambda a: "news.google.com" in a["url"])[:6]
            r["marked"] = "News: story" in (r["use"] or "") or "News: rumor" in (r["use"] or "")
            r["rumor"] = "News: rumor" in (r["use"] or "")
            r["quick"] = "News: quick" in (r["use"] or "") and not r["marked"]
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    print("%d candidates (%d marked News: story or rumor, %d News: quick) from the last %d days."
          % (len(rows), sum(r["marked"] for r in rows), sum(r.get("quick", False) for r in rows), days), file=sys.stderr)


def done():
    items, _ = on_site()
    print("%d Studio stories are on the site: %s" % (len(items), ", ".join(map(str, sorted(items)))))


# "➕ 10 more stories" on the script page (Kevin, 3 Nov 2026: "just have a button in the prompter that can always add more
# stories from our resources to load up the next 10 best"): the Studio keeps the request in settings 'news_more' and
# starts the news run; NEWS.md "More stories on request" says what the run does with it.
def more(args):
    rows = query("SELECT value FROM settings WHERE key = 'news_more'")
    req = json.loads(rows[0]["value"]) if rows and rows[0].get("value") else {}
    if "--done" in args:
        if req.get("status") != "asked":
            print("No request waiting.")
            return
        req.update(status="done", added=int(args[args.index("--done") + 1]), done_at=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        query("UPDATE settings SET value = ? WHERE key = 'news_more'", [json.dumps(req)])
        print("Marked done: %d more stories." % req["added"])
        return
    print(json.dumps({"waiting": req.get("status") == "asked", "n": req.get("n", 10), "asked_at": req.get("at"), "by": req.get("by")}))


# New apps climbing the App Store charts (Kevin, 3 Nov 2026: "rising starts in the app stores ... we can talk about the
# top 10 new apps in each category"): the Studio's "Rising apps" sources keep apps out less than 60 days that are in the
# top 100 of a category, the whole store or the Mac App Store. Grouped by category for the weekly roundups (NEWS.md).
def rising(days):
    _, urls = on_site()
    rows = query("""SELECT i.id, i.title, i.url, i.snippet, i.published, i.score, i.ai_summary AS summary, i.ai_use AS use
        FROM items i JOIN sources s ON s.id = i.source_id
        WHERE s.grp = 'Rising apps' AND i.published >= datetime('now', ?) AND COALESCE(i.ai_use, '') NOT LIKE 'Skip%'
        ORDER BY i.score DESC""", ["-%d days" % days])
    groups = {}
    for r in rows:
        m = re.match(r"^(.*): new app at #(\d+) in (.+)$", r["title"] or "")
        if not m:
            continue
        name, rank, chart = m.group(1), int(m.group(2)), m.group(3)
        bits = (r["snippet"] or "").split(" · ")
        genre = chart.split(", ")[0] if ", " in chart else (bits[3] if len(bits) > 3 else "Other")
        key = "Mac apps" if "Mac App Store" in chart else genre
        groups.setdefault(key, []).append({"id": r["id"], "name": name, "rank": rank, "chart": chart, "url": r["url"],
            "out_since": bits[0].replace("Out since ", "") if bits and bits[0].startswith("Out since") else "",
            "maker": bits[1] if len(bits) > 1 else "", "price": bits[2] if len(bits) > 2 else "",
            "about": " · ".join(bits[4:]), "summary": r["summary"], "card": r["use"], "on_site": norm(r["url"]) in urls})
    out = sorted(groups.items(), key=lambda g: -len(g[1]))
    print(json.dumps(dict(out), ensure_ascii=False, indent=1))
    print("%d new apps in %d categories from the last %d days (the AI's skips left out)."
          % (sum(len(v) for _, v in out), len(out), days), file=sys.stderr)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["todo"]:
        todo(int(args[args.index("--days") + 1]) if "--days" in args else 3)
    elif args[:1] == ["done"]:
        done()
    elif args[:1] == ["more"]:
        more(args)
    elif args[:1] == ["rising"]:
        rising(int(args[args.index("--days") + 1]) if "--days" in args else 7)
    else:
        sys.exit(__doc__)
