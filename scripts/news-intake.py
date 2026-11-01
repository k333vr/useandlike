#!/usr/bin/env python3
"""The day's story candidates for useandlike.com/news: the Studio's (studio.useandlike.com) rated stories from the last
days that aren't on the site yet. The daily news run reads them, checks each source and writes data/news/<slug>.json
(see NEWS.md).

    python3 scripts/news-intake.py todo [--days 3]   # JSON list, best first
    python3 scripts/news-intake.py done              # which Studio stories are on the site (item ids from data/news)

A candidate is a story the morning AI marked "News: story" (Kevin, 1 Nov 2026: "basically no limit and also a lot of
newcomer apps") or "News: rumor" (a rumor, leak or feature in testing: Kevin wants those too, framed as such; "rumor": true),
or one it marked for the newsletter or scored 60+, unless it wrote "Skip". Each comes with the other outlets that reported
the same news ("also"), so a fact can be checked in a second source.
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
          AND (i.ai_use LIKE '%News: story%' OR i.ai_use LIKE '%News: rumor%' OR i.ai_use LIKE '%Newsletter:%' OR i.ai_score >= 60)
          AND COALESCE(i.ai_use, '') NOT LIKE 'Skip%'
        ORDER BY (i.ai_use LIKE '%News: %') DESC, i.ai_score DESC, i.sources_count DESC""", ["-%d days" % days])
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
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    print("%d candidates (%d marked News: story or rumor) from the last %d days." % (len(rows), sum(r["marked"] for r in rows), days),
          file=sys.stderr)


def done():
    items, _ = on_site()
    print("%d Studio stories are on the site: %s" % (len(items), ", ".join(map(str, sorted(items)))))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["todo"]:
        todo(int(args[args.index("--days") + 1]) if "--days" in args else 3)
    elif args[:1] == ["done"]:
        done()
    else:
        sys.exit(__doc__)
