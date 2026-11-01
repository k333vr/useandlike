#!/usr/bin/env python3
"""The presenter's scripts for the day's stories, saved into the Studio (studio.useandlike.com), where she reads them on
scripts.useandlike.com (see NEWS.md, "Scripts for the presenter").

    python3 scripts/news-scripts.py save /tmp/scripts.json    # add the day's scripts (a script she already worked on stays)
    python3 scripts/news-scripts.py list [--day 2026-11-02]   # what's there and its status

/tmp/scripts.json: a list of
    {"code": "N1102-01", "day": "2026-11-02", "rank": 1, "slug": "<story slug>", "item": 13433,
     "head": "<the story's headline>", "facts": ["<checked fact>", ...], "sources": [{"name": "...", "url": "https://..."}],
     "versions": [{"label": "A", "text": "..."}, {"label": "B", "text": "..."}, {"label": "C", "text": "..."}],
     "title": "<YouTube title>", "description": "<YouTube description>"}
Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID (the Studio's database is Cloudflare D1 "useandlike-studio").
"""
import json, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ID = "8209584b-6109-45f6-9367-5befe0f080a5"   # D1 "useandlike-studio" (useandlike-ops/studio/wrangler.toml)
HYPE = re.compile(r"\b(best|cheapest|fastest|greatest|ultimate|unbeatable|game[- ]changer|must[- ]have|insane|crazy|"
                  r"mind[- ]blowing|shocking|you won't believe|number one|#1)\b", re.I)


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


def words(t):
    return len(re.findall(r"[\w'’$%.-]+", t or ""))


def problems(s, slugs):
    out = []
    if not re.fullmatch(r"N\d{4}-\d{2}", str(s.get("code", ""))):
        out.append('code should look like "N1102-01" (month, day, rank)')
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s.get("day", ""))):
        out.append('day should look like "2026-11-02"')
    elif s.get("code", "")[1:5] != s["day"][5:7] + s["day"][8:10]:
        out.append("the code's month and day don't match day")
    if not str(s.get("head", "")).strip():
        out.append("head is missing")
    if s.get("slug") and s["slug"] not in slugs:
        out.append("slug %s isn't a story in data/news/" % s["slug"])
    v = s.get("versions") or []
    if len(v) < 3:
        out.append("needs 3 versions (A, B, C)")
    for x in v:
        t = str(x.get("text", ""))
        n = words(t)
        if n < 50 or n > 360:
            out.append("version %s has %d words (50-360)" % (x.get("label", "?"), n))
        if HYPE.search(t):
            out.append('version %s uses "%s" (no hype)' % (x.get("label", "?"), HYPE.search(t).group(0)))
        if re.search(r"https?://|www\.", t):
            out.append("version %s has a web address: say \"useandlike dot com\" instead" % x.get("label", "?"))
    if len(str(s.get("title", ""))) > 100 or not str(s.get("title", "")).strip():
        out.append("title is missing or longer than 100 characters (aim for 60)")
    if not str(s.get("description", "")).strip():
        out.append("description is missing")
    for src in s.get("sources") or []:
        if not str(src.get("url", "")).startswith("https://"):
            out.append("source %s needs an https link" % src.get("name", "?"))
    return out


def save(path):
    scripts = json.load(open(path, encoding="utf-8"))
    slugs = {f[:-5] for f in os.listdir(os.path.join(ROOT, "data", "news")) if f.endswith(".json")}
    bad = [(s.get("code", "?"), p) for s in scripts for p in problems(s, slugs)]
    if bad:
        for code, p in bad:
            print("%s: %s" % (code, p))
        sys.exit("Nothing saved: fix the problems above.")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    added = updated = kept = 0
    for s in scripts:
        old = query("SELECT status, edited FROM scripts WHERE code = ?", [s["code"]])
        vals = [s["day"], int(s.get("rank") or 99), s.get("slug"), s.get("item"), s["head"][:300],
                json.dumps([str(f)[:300] for f in s.get("facts") or []][:12], ensure_ascii=False),
                json.dumps(s.get("sources") or [], ensure_ascii=False),
                json.dumps([{"label": str(x.get("label") or chr(65 + i))[:20], "text": str(x["text"]).strip()[:6000]}
                            for i, x in enumerate(s["versions"])], ensure_ascii=False),
                s["title"][:200], s["description"][:3000]]
        if not old:
            query("""INSERT INTO scripts (code, day, rank, slug, item_id, head, facts, sources, versions, title, description, created)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [s["code"]] + vals + [now])
            added += 1
        elif old[0]["status"] == "draft" and not old[0]["edited"]:
            query("""UPDATE scripts SET day = ?, rank = ?, slug = ?, item_id = ?, head = ?, facts = ?, sources = ?, versions = ?,
                     title = ?, description = ?, chosen = 0, updated = ?, updated_by = 'news run' WHERE code = ?""",
                  vals + [now, s["code"]])
            updated += 1
        else:
            kept += 1     # she already approved, edited, flagged or recorded it: her work stays
    print("Scripts: %d added, %d updated, %d left as they were (already worked on)." % (added, updated, kept))


def show(day):
    rows = query("SELECT code, status, head, updated_by FROM scripts WHERE day = ? ORDER BY rank, id", [day]) if day else \
        query("SELECT code, status, head, updated_by FROM scripts ORDER BY day DESC, rank LIMIT 40")
    for r in rows:
        print("%s  %-9s %s" % (r["code"], r["status"], r["head"]))
    print("%d scripts." % len(rows))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["save"] and len(a) > 1:
        save(a[1])
    elif a[:1] == ["list"]:
        show(a[a.index("--day") + 1] if "--day" in a else None)
    else:
        sys.exit(__doc__)
