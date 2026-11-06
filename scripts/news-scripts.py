#!/usr/bin/env python3
"""The presenter's scripts for the day's stories, saved into the Studio (studio.useandlike.com), where she reads them on
scripts.useandlike.com (see NEWS.md, "Scripts for the presenter").

    python3 scripts/news-scripts.py save /tmp/scripts.json    # add the day's scripts (a script she already worked on stays)
    python3 scripts/news-scripts.py list [--day 2026-11-02]   # what's there and its status

/tmp/scripts.json: a list of
    {"code": "N1102-01", "day": "2026-11-02", "rank": 1, "slug": "<story slug>", "item": 13433,
     "head": "<the story's headline>", "facts": ["<checked fact>", ...], "sources": [{"name": "...", "url": "https://..."}],
     "versions": [{"label": "A", "text": "..."}, {"label": "B", "text": "..."}, {"label": "C", "text": "..."}],
     "chosen": "B",   # the version her teleprompter reads by default (NEWS.md: big stories B, small ones C, the rest A)
     # a rare long one adds a 4th version {"label": "L", "text": "..."} (250-1,300 words, 2-8 minutes) and "chosen": "L"
     "takes": ["<a one-line reaction she can pick>", ...], "points": ["<3-6 key points, a few words each>", ...],
     "title": "<YouTube title>", "description": "<YouTube description>",
     "pinned": "<one short question for the pinned comment, e.g. Would you lock your chats with a PIN?>"}
Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID (the Studio's database is Cloudflare D1 "useandlike-studio").
"""
import json, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ID = "8209584b-6109-45f6-9367-5befe0f080a5"   # D1 "useandlike-studio" (useandlike-ops/studio/wrangler.toml)
HYPE = re.compile(r"\b(best|cheapest|fastest|greatest|ultimate|unbeatable|game[- ]changer|must[- ]have|insane|crazy|"
                  r"mind[- ]blowing|shocking|you won't believe|number one|#1)\b", re.I)
# Kevin, 1 Nov: no spoken subscribe or newsletter reminder in these short videos; the end card shows them.
CTA = re.compile(r"\b(subscribe|newsletter|useandlike|dot com|link in the description|like and)\b", re.I)


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
    labels = [str(x.get("label") or chr(65 + i)) for i, x in enumerate(v)]
    if s.get("chosen") not in (None, "") and str(s["chosen"]) not in labels:
        out.append("chosen %r isn't one of the versions (%s)" % (s["chosen"], ", ".join(labels)))
    for x in v:
        t = str(x.get("text", ""))
        n = words(t)
        # Kevin, 6 Nov: a big story may run 2-3 minutes (B), and now and then a long one 2-8 minutes (an extra version L)
        least, most = (250, 1300) if x.get("label") == "L" else (40, 450 if x.get("label") == "B" else 300)
        if n < least or n > most:
            out.append("version %s has %d words (%d-%d)" % (x.get("label", "?"), n, least, most))
        if CTA.search(t):
            out.append('version %s says "%s": no spoken call to action or web address (the end card shows them)'
                       % (x.get("label", "?"), CTA.search(t).group(0)))
        if HYPE.search(t):
            out.append('version %s uses "%s" (no hype)' % (x.get("label", "?"), HYPE.search(t).group(0)))
        if re.search(r"https?://|www\.", t):
            out.append("version %s has a web address: say \"useandlike dot com\" instead" % x.get("label", "?"))
    for t in s.get("takes") or []:
        if len(str(t)) > 160 or HYPE.search(str(t)):
            out.append("take %r: at most one short line, no hype" % str(t)[:40])
    # Key points (1 Nov): what the teleprompter shows in "Key points" mode, so she can say it in her own words.
    # A roundup ("list" in its story: new apps of the week) gets one point per app, up to 10.
    most = 10 if roundup(s.get("slug")) else 6
    pts = s.get("points") or []
    if not 3 <= len(pts) <= most:
        out.append("needs 3-%d key points (a few words each, in speaking order)" % most)
    for t in pts:
        if len(str(t)) > 70 or HYPE.search(str(t)) or CTA.search(str(t)):
            out.append("point %r: at most 70 characters, no hype, no call to action" % str(t)[:40])
    if len(str(s.get("title", ""))) > 100 or not str(s.get("title", "")).strip():
        out.append("title is missing or longer than 100 characters (aim for 60)")
    if not str(s.get("description", "")).strip():
        out.append("description is missing")
    for src in s.get("sources") or []:
        if not str(src.get("url", "")).startswith("https://"):
            out.append("source %s needs an https link" % src.get("name", "?"))
    return out


def roundup(slug):
    f = os.path.join(ROOT, "data", "news", "%s.json" % slug)
    try:
        return bool(json.load(open(f, encoding="utf-8")).get("list"))
    except (OSError, ValueError):
        return False


def save(path):
    scripts = json.load(open(path, encoding="utf-8"))
    slugs = {f[:-5] for f in os.listdir(os.path.join(ROOT, "data", "news")) if f.endswith(".json")}
    bad = [(s.get("code", "?"), p) for s in scripts for p in problems(s, slugs)]
    if bad:
        for code, p in bad:
            print("%s: %s" % (code, p))
        sys.exit("Nothing saved: fix the problems above.")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    added = updated = kept = linked = moved = 0
    for s in scripts:
        # The Studio wrote this story's script on the spot when her list ran low (origin "instant", 6 Nov): give that
        # script the story's page instead of adding a second script for the same news.
        inst = query("SELECT id, day, status FROM scripts WHERE item_id = ? AND origin = 'instant'", [s.get("item")]) if s.get("item") else []
        if inst:
            query("UPDATE scripts SET slug = ? WHERE id = ? AND (slug IS NULL OR slug = '')", [s.get("slug"), inst[0]["id"]])
            linked += 1
            # Written before this run, it waits on an older day's list, and she only sees the newest day: it moves to
            # this day at this story's place (her own work on it stays; recorded ones stay where they are).
            if inst[0]["day"] < s["day"] and inst[0]["status"] in ("draft", "approved"):
                code, rank = free_code(s["day"], s["code"], int(s.get("rank") or 99))
                query("UPDATE scripts SET day = ?, rank = ?, code = ?, updated = ?, updated_by = 'news run' WHERE id = ?",
                      [s["day"], rank, code, now, inst[0]["id"]])
                moved += 1
            continue
        old = query("SELECT status, edited, item_id FROM scripts WHERE code = ?", [s["code"]])
        if old and old[0]["item_id"] is not None and str(old[0]["item_id"]) != str(s.get("item")):
            # Another story holds this number (the Studio's instant writer also numbers after the day's last script):
            # this story keeps its own number from an earlier save of this run, else takes the day's next free one.
            mine = query("SELECT code, rank FROM scripts WHERE item_id = ? AND day = ?", [s.get("item"), s["day"]]) if s.get("item") else []
            s["code"], s["rank"] = (mine[0]["code"], mine[0]["rank"]) if mine else free_code(s["day"], None, 99)
            old = query("SELECT status, edited, item_id FROM scripts WHERE code = ?", [s["code"]])
        labels = [str(x.get("label") or chr(65 + i)) for i, x in enumerate(s["versions"])]
        chosen = labels.index(str(s["chosen"])) if str(s.get("chosen") or "") in labels else 0
        vals = [s["day"], int(s.get("rank") or 99), s.get("slug"), s.get("item"), s["head"][:300],
                json.dumps([str(f)[:300] for f in s.get("facts") or []][:12], ensure_ascii=False),
                json.dumps(s.get("sources") or [], ensure_ascii=False),
                json.dumps([{"label": str(x.get("label") or chr(65 + i))[:20], "text": str(x["text"]).strip()[:6000]}
                            for i, x in enumerate(s["versions"])], ensure_ascii=False),
                s["title"][:200], s["description"][:3000],
                json.dumps([str(t).strip()[:160] for t in s.get("takes") or []][:4], ensure_ascii=False),
                json.dumps([str(t).strip()[:70] for t in s.get("points") or []][:10 if roundup(s.get("slug")) else 6], ensure_ascii=False),
                (str(s.get("pinned") or "").strip()[:120] or None)]
        if not old:
            query("""INSERT INTO scripts (code, day, rank, slug, item_id, head, facts, sources, versions, title, description, takes, points,
                     pinned, chosen, created, writer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'news run')""", [s["code"]] + vals + [chosen, now])
            added += 1
        elif old[0]["status"] == "draft" and not old[0]["edited"]:
            query("""UPDATE scripts SET day = ?, rank = ?, slug = ?, item_id = ?, head = ?, facts = ?, sources = ?, versions = ?,
                     title = ?, description = ?, takes = ?, points = ?, pinned = ?, chosen = ?, updated = ?, updated_by = 'news run',
                     writer = COALESCE(writer, 'news run')
                     WHERE code = ?""", vals + [chosen, now, s["code"]])
            updated += 1
        else:
            kept += 1     # she already approved, edited, flagged or recorded it: her work stays
            if vals[-1]:  # the uploader's pinned question isn't her work: it may still come in
                query("UPDATE scripts SET pinned = ? WHERE code = ? AND (pinned IS NULL OR pinned = '')", [vals[-1], s["code"]])
    print("Scripts: %d added, %d updated, %d left as they were (already worked on), %d instant ones linked to their story"
          " (%d of them moved to this day's list)." % (added, updated, kept, linked, moved))


def free_code(day, code, rank):
    """The code and rank to use on this day: the given ones if the code is free, else the day's next free number."""
    if code and not query("SELECT 1 AS x FROM scripts WHERE code = ?", [code]):
        return code, rank
    r = (query("SELECT MAX(rank) AS r FROM scripts WHERE day = ?", [day]) or [{}])[0].get("r") or 0
    while True:
        r += 1
        c = "N%s%s-%02d" % (day[5:7], day[8:10], r)
        if not query("SELECT 1 AS x FROM scripts WHERE code = ?", [c]):
            return c, r


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
