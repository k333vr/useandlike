#!/usr/bin/env python3
"""X posts about the day's stories, for the presenter's "What people say" box and the video's "ON X" card (15 Nov 2026).

Kevin, 13-14 Nov: "track those also in some way for each article to might find interesting reviews, opinions or
comments"; "if something goes viral and we credited (or showed the X user name) we might get exposure ... as long as its
100% safe for youtube". Rules: NEWS.md "What people say".

One X search per full story about a known company or product (small new App Store apps are skipped: on 14 Nov 16 of
~25 had no posts or only name clashes), through Apify (Kevin's account; the key is the cloud environment's network
secret for api.apify.com, so this runs in the news session, not in the Studio's Worker): scrape.badger's
twitter-tweets-scraper, Advanced Search, Top, the last 3 days, 15 posts at most (about $0.15 per 1,000 posts; it stops
at $3 a month, the free credit is $5). Kept: English, the app or company named in the text, the maker's own account or
10k+ followers, plus opinions with many likes from smaller accounts. Written into the Studio's reactions table (D1).
on_screen_ok = 1 when the post may be shown in the video: text only (no photo or video), not a reply, and none of the
never-on-screen things below (a first filter; the swear words are starred on the card itself).

  python3 scripts/x-reactions.py            the newest script day (the day the news run just saved)
  python3 scripts/x-reactions.py 2026-11-14 that day
  python3 scripts/x-reactions.py --dry      show what would be kept, write nothing (the searches still cost)
  --limit=N                                 at most N stories

Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID (D1) and the Apify network secret (sent as "proxy-injected").
"""
import concurrent.futures as cf, html, json, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_ID = "8209584b-6109-45f6-9367-5befe0f080a5"
ACTOR = "https://api.apify.com/v2/acts/scrape.badger~twitter-tweets-scraper/run-sync-get-dataset-items?timeout=270"
PER_POST = 0.00015                    # dollars per post returned
MONTH_CAP = 3.0                       # dollars a month (Kevin's free credit is $5)
MAX_STORIES = 60

STOP = set(("a an the and or of to in on for with by at from is are was its it this that new now out how why what your you can "
            "will gets get adds add more about after over into up down vs app apps update november december october").split())
# Never on screen, even starred (Kevin, 15 Nov: "slurs or very harsh opinions or something outlandish we can censor it and
# make a joke over it"; strong opinions are welcome, but YouTube's hate and harassment rules apply to the whole video):
# slurs and attacks on people for who they are, threats, adult content, politics, medical or money claims, personal data,
# children. A first filter only; the director and the editor's eye do the rest.
NEVER = re.compile(r"\b(n[i1]gg\w*|f[a4]gg?[o0]t\w*|retard\w*|tranny|k[i1]ke|sp[i1]c|ch[i1]nk|wetback|"
                   r"kill (yo)?u|kill (him|her|them)|kys|die in|shoot|bomb|rape\w*|nazi\w*|hitler|"
                   r"porn\w*|nsfw|nude\w*|onlyfans|sex\w*|horny|"
                   r"trump|biden|harris|vance|musk|democrat\w*|republican\w*|maga|liberal\w*|leftist\w*|election\w*|gaza|israel\w*|"
                   r"palestin\w*|ukraine|russia\w*|putin|abortion|immigra\w*|"
                   r"cure\w*|cancer|vaccin\w*|covid|diagnos\w*|invest\w*|crypto\w*|bitcoin|stock (price|tip)|guaranteed|profit\w*|"
                   r"my (son|daughter|kid|kids|child)|minor|teen\w*|"
                   r"allegedly|rumou?red to be|is a (scammer|fraud|liar|criminal))\b", re.I)
PERSONAL = re.compile(r"(\b\d{3}[-. ]\d{3}[-. ]\d{4}\b|[\w.+-]+@[\w-]+\.[a-z]{2,})", re.I)


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
                sys.exit("Database error: %s" % (e.read().decode()[:300] if isinstance(e, urllib.error.HTTPError) else e))
            time.sleep(2 ** attempt)


def alnum(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def story_of(slug):
    try:
        return json.load(open(os.path.join(ROOT, "data", "news", "%s.json" % slug), encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def plan(s):
    """(app, query) for a script, or (None, why) when it's skipped."""
    info = {}
    try:
        info = json.loads(s.get("traction_info") or "{}") or {}
    except ValueError:
        pass
    page = story_of(s.get("slug")) if s.get("slug") else {}
    apps = [a if isinstance(a, str) else (a or {}).get("name", "") for a in (page.get("apps") or [])]
    app = (apps[0] if apps else "") or info.get("app") or ""
    if not app:
        return None, "no app"
    if page.get("list"):
        return None, "a roundup"
    # a known company or product: the press has it, or people search it or make videos about it
    known = (info.get("outlets") or 0) >= 3 or (info.get("suggest") or 0) >= 5 or (info.get("videos") or 0) >= 1
    if not known or (page.get("tag") == "New app" and (info.get("outlets") or 0) < 3):
        return None, "a small app"
    words = [w for w in re.findall(r"[A-Za-z][\w.+-]*", s.get("head") or "")
             if len(w) > 3 and w.lower() not in STOP and alnum(w) not in alnum(app)]
    since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    return app, ('"%s" %s lang:en since:%s' % (app, words[0] if words else "", since)).replace("  ", " ")


def search(q):
    body = json.dumps({"mode": "Advanced Search", "query": q, "query_type": "Top", "max_results": 15}).encode()
    req = urllib.request.Request(ACTOR, body, {"Content-Type": "application/json", "Authorization": "Bearer proxy-injected"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=290))
    except Exception as e:
        return {"error": str(e)[:200]}
    return [t for t in d if isinstance(t, dict) and t.get("text") and not t.get("noResults")] if isinstance(d, list) else []


def judge(t, app, head):
    """-> None (not kept) or (row fields, on_screen_ok)."""
    text = html.unescape(re.sub(r"https?://\S+", "", t.get("full_text") or t.get("text") or "")).strip()
    letters = len(re.findall(r"[^\W\d_]", text))
    if t.get("lang") not in (None, "en") or t.get("is_retweet") or letters < 40 or letters > 700:
        return None
    if not re.search(r"\b%s\b" % re.escape(app), text, re.I):
        return None
    handle, name, fol, likes = t.get("username") or "", t.get("user_name") or "", t.get("user_followers_count") or 0, t.get("favorite_count") or 0
    key = alnum(handle)[:6] or "-"
    maker = len(key) >= 4 and fol >= 5000 and (key in alnum(head) or alnum(app)[:6] in alnum(handle + name))
    if not (maker or fol >= 10000 or likes >= 200):
        return None
    mentions = [m.get("username", "").lower() for m in (t.get("user_mentions") or [])]
    reply = t.get("conversation_id") and t.get("conversation_id") != t.get("id")
    ok = (not t.get("media") and not reply and not NEVER.search(text) and not PERSONAL.search(text)
          and (maker or fol >= 10000 or likes >= 500)
          and all(alnum(m)[:5] in alnum(head) for m in mentions))        # @mentions only of the companies in the story
    try:
        posted = datetime.strptime(t.get("created_at", ""), "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        posted = None
    return dict(author=name[:80], handle=handle[:40], followers=fol, text=text[:1200], likes=likes, posted=posted,
                url="https://x.com/%s/status/%s" % (handle, t.get("id")), maker=bool(maker)), ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    limit = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), MAX_STORIES)
    day = args[0] if args else (query("SELECT MAX(day) AS d FROM scripts")[0]["d"])
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    used = {}
    try:
        used = json.loads((query("SELECT value FROM settings WHERE key = 'x_reactions_spend'") or [{}])[0].get("value") or "{}")
    except ValueError:
        pass
    if used.get("month") != month:
        used = {"month": month, "posts": 0}
    left = int((MONTH_CAP - used["posts"] * PER_POST) / PER_POST)
    rows = query("""SELECT s.id, s.item_id, s.slug, s.head, i.traction_info FROM scripts s LEFT JOIN items i ON i.id = s.item_id
                    WHERE s.day = ? AND s.status != 'struck'
                      AND NOT EXISTS (SELECT 1 FROM reactions r WHERE r.script_id = s.id AND r.platform = 'x') ORDER BY s.rank""", [day])
    todo, skipped = [], {}
    for s in rows:
        app, q = plan(s)
        if app:
            todo.append((s, app, q))
        else:
            skipped[q] = skipped.get(q, 0) + 1
    todo = todo[:min(limit, max(0, left // 15))]
    print("day %s: %d scripts, %d to search (skipped: %s); this month %d posts ($%.2f of $%.0f)" % (
        day, len(rows), len(todo), ", ".join("%d %s" % (n, w) for w, n in skipped.items()) or "none", used["posts"], used["posts"] * PER_POST, MONTH_CAP))
    if not todo:
        return
    with cf.ThreadPoolExecutor(5) as ex:
        found = list(ex.map(lambda x: search(x[2]), todo))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    got = kept = shown = 0
    stmts = []
    for (s, app, q), posts in zip(todo, found):
        if isinstance(posts, dict):
            print("  %s: %s" % (s["head"][:60], posts["error"]))
            continue
        got += len(posts)
        best = []
        for t in posts:
            j = judge(t, app, s["head"])
            if j:
                best.append(j)
        best.sort(key=lambda j: (not j[0]["maker"], -(j[0]["likes"] or 0)))
        for r, ok in best[:6]:
            kept += 1
            shown += ok
            if dry:
                print("  %s | @%s %s fol %s likes%s | %s" % (s["head"][:40], r["handle"], r["followers"], r["likes"], " ON SCREEN OK" if ok else "",
                                                         r["text"][:110].replace("\n", " ")))
                continue
            stmts.append(("INSERT OR IGNORE INTO reactions (script_id, item_id, platform, author, handle, followers, text, url, likes, posted, fetched, info, on_screen_ok) "
                          "VALUES (?, ?, 'x', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          [s["id"], s["item_id"], r["author"], r["handle"], r["followers"], r["text"], r["url"], r["likes"], r["posted"], now,
                           json.dumps({"maker": r["maker"], "where": q}), 1 if ok else 0]))
    for sql, params in stmts:
        query(sql, params)
    used["posts"] += got
    if not dry:
        query("INSERT INTO settings (key, value) VALUES ('x_reactions_spend', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", [json.dumps(used)])
    print("X: %d posts read (~$%.2f), %d kept for %d stories, %d may go on screen; month so far $%.2f" % (
        got, got * PER_POST, kept, len(todo), shown, used["posts"] * PER_POST))


if __name__ == "__main__":
    main()
