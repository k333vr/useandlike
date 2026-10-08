#!/usr/bin/env python3
"""Puts our links at the top of old YouTube video descriptions: videos with a tool link first, then the rest,
each group most viewed first. Music videos (DJ remixes etc.) are skipped.

Each video gets the same lines as in the editor lists (scripts/build-editor-lists.py):
    👉 Try <Tool> (affiliate): useandlike.com/<slug>      (only when the title names one of our tools)
    📩 Join Our Newsletter & Get Free Subscription Tracker: useandlike.com/join
followed by an empty line and the old description, unchanged. Titles, tags and everything else stay as they are.
Videos whose description already has useandlike.com/join are skipped (running it again is safe),
except that the tool line is added on top when that video's tool was added to the site later.

Setup (once): YT_CLIENT_ID and YT_CLIENT_SECRET from a Google Cloud OAuth client of type
"TVs and Limited Input devices", with the YouTube Data API v3 enabled.

    python3 scripts/youtube-descriptions.py login htr      # sign in with the How To Rocket channel (code on google.com/device)
    python3 scripts/youtube-descriptions.py run htr        # preview only: writes editors/youtube-preview-htr.csv
    python3 scripts/youtube-descriptions.py run htr --apply --limit 95

YouTube's free quota is 10,000 units a day per Google Cloud project, shared by all channels (resets at midnight
Pacific time): an update costs 50, reading one channel's video list about 200 for 5,000 videos, so about
190 updates a day in total, e.g. --limit 95 for each of the two channels.
Sign-in tokens are saved in ~/.config/useandlike-youtube/ (never in the repo), or read from the environment
variable YT_REFRESH_TOKEN_<NAME> (e.g. YT_REFRESH_TOKEN_HTR).
"""
import csv, datetime, importlib.util, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_DIR = os.path.expanduser("~/.config/useandlike-youtube")
SCOPE = "https://www.googleapis.com/auth/youtube"
API = "https://www.googleapis.com/youtube/v3/"
MARKER = "useandlike.com/join"
MAX_DESCRIPTION = 5000
# Music uploads (Rajasthani/Marwadi DJ remixes on How To Rocket): their viewers are not our newsletter's audience
MUSIC = re.compile(r"\bdj\b|remix|rajasthani|marwadi|bhajan|bhakti|dholki|bass mix|[\u0900-\u097F]", re.I)

spec = importlib.util.spec_from_file_location("lists", os.path.join(ROOT, "scripts", "build-editor-lists.py"))
lists = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lists)


def post(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode() or "{}")


def client():
    try:
        return os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"]
    except KeyError:
        sys.exit("Set YT_CLIENT_ID and YT_CLIENT_SECRET first (see the top of this file).")


def login(name):
    cid, secret = client()
    r = post("https://oauth2.googleapis.com/device/code", {"client_id": cid, "scope": SCOPE})
    if "device_code" not in r:
        sys.exit("Google refused the sign-in: %s" % r)
    print("\nOn your phone or computer open:  %s\nand enter the code:  %s\n" % (r["verification_url"], r["user_code"]))
    print("Choose the Google account, then the channel (%s), and allow access. Waiting..." % name.upper())
    while True:
        time.sleep(r.get("interval", 5))
        t = post("https://oauth2.googleapis.com/token", {"client_id": cid, "client_secret": secret, "device_code": r["device_code"],
                                                         "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
        if "refresh_token" in t:
            os.makedirs(TOKEN_DIR, mode=0o700, exist_ok=True)
            path = os.path.join(TOKEN_DIR, name + ".json")
            with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
                json.dump({"refresh_token": t["refresh_token"]}, f)
            access = t["access_token"]
            ch = api("GET", "channels", {"part": "snippet", "mine": "true"}, access)["items"][0]["snippet"]["title"]
            print("Signed in as the channel: %s (saved for '%s')" % (ch, name))
            return
        if t.get("error") not in ("authorization_pending", "slow_down"):
            sys.exit("Sign-in stopped: %s" % t.get("error_description", t))


def access_token(name):
    cid, secret = client()
    refresh = os.environ.get("YT_REFRESH_TOKEN_" + name.upper())
    if not refresh:
        path = os.path.join(TOKEN_DIR, name + ".json")
        if not os.path.exists(path):
            sys.exit("Not signed in for '%s' yet: run  python3 scripts/youtube-descriptions.py login %s" % (name, name))
        refresh = json.load(open(path))["refresh_token"]
    t = post("https://oauth2.googleapis.com/token", {"client_id": cid, "client_secret": secret,
                                                     "refresh_token": refresh, "grant_type": "refresh_token"})
    if "access_token" not in t:
        sys.exit("Sign-in expired for '%s': run login again. (%s)" % (name, t.get("error", t)))
    return t["access_token"]


class QuotaExceeded(Exception):
    pass


def api(method, path, params, token, body=None):
    url = API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, json.dumps(body).encode() if body else None, method=method,
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        if "quotaExceeded" in err or "dailyLimitExceeded" in err:
            raise QuotaExceeded()
        raise RuntimeError("YouTube API %s %s: %s" % (e.code, path, err[:400]))


def seconds(iso):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    d, h, mi, s = (int(x or 0) for x in m.groups()) if m else (0, 0, 0, 0)
    return d * 86400 + h * 3600 + mi * 60 + s


def all_videos(token):
    ch = api("GET", "channels", {"part": "snippet,contentDetails", "mine": "true"}, token)["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        params = {"part": "contentDetails", "playlistId": uploads, "maxResults": 50}
        if page:
            params["pageToken"] = page
        r = api("GET", "playlistItems", params, token)
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        page = r.get("nextPageToken")
        if not page:
            break
    videos = []
    for i in range(0, len(ids), 50):
        r = api("GET", "videos", {"part": "snippet,statistics,contentDetails,status", "id": ",".join(ids[i:i + 50])}, token)
        videos += r["items"]
    return ch["snippet"]["title"], videos


def run(name, apply, limit):
    token = access_token(name)
    lines_for = lists.make_matcher(lists.load_tools())
    channel, videos = all_videos(token)
    print("Channel: %s, %d videos" % (channel, len(videos)))

    todo, seen = [], set()
    for v in videos:
        sn = v["snippet"]
        if v["id"] in seen or sn.get("liveBroadcastContent", "none") != "none":
            continue
        seen.add(v["id"])
        if MUSIC.search(sn["title"]):
            continue
        if seconds(v["contentDetails"].get("duration")) <= 60:      # Shorts: links in their descriptions can't be clicked
            continue
        kind, lines = lines_for(sn["title"])
        desc = sn.get("description", "")
        if MARKER in desc:
            # Already has our links: only add the tool line when the video's tool was added to the site later.
            if kind != "tool" or "\U0001F449" in desc[:400]:
                continue
            new, kind = lines[0] + "\n" + desc, "tool line added"
        else:
            new = "\n".join(lines) + "\n\n" + desc
        todo.append((int(v["statistics"].get("viewCount", 0)), v, kind, new))
    todo.sort(key=lambda t: -t[0])   # most viewed first (owner, 8 Oct): the newsletter line matters on every big video
    print("%d videos still need the links (most viewed first)." % len(todo))

    os.makedirs(os.path.join(ROOT, "editors"), exist_ok=True)
    out = os.path.join(ROOT, "editors", "youtube-%s-%s.csv" % ("updated" if apply else "preview", name))
    done = 0
    with open(out, "a" if apply else "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not apply or f.tell() == 0:
            w.writerow(["Date", "Views", "Video", "Title", "Type", "Result", "New description (start)"])
        for views, v, kind, new in todo[:limit]:
            sn = v["snippet"]
            link = "https://youtu.be/" + v["id"]
            if len(new.encode("utf-8")) > MAX_DESCRIPTION:   # YouTube counts bytes
                result = "skipped: description would be too long"
            elif not apply:
                result = "preview"
            else:
                body = {"id": v["id"], "snippet": {k: sn[k] for k in ("title", "categoryId", "tags", "defaultLanguage",
                                                                       "defaultAudioLanguage") if k in sn}}
                body["snippet"]["description"] = new
                try:
                    api("PUT", "videos", {"part": "snippet"}, token, body)
                    result, done = "updated", done + 1
                except QuotaExceeded:
                    print("Today's YouTube quota is used up. Run again tomorrow; it continues where it stopped.")
                    break
                except RuntimeError as e:
                    result = "error: " + str(e)[:200]
            w.writerow([datetime.date.today().isoformat(), views, link, sn["title"], kind, result, new[:300]])
    print(("Updated %d videos." % done) if apply else "Preview written (nothing changed on YouTube).")
    print("List: " + os.path.relpath(out, ROOT))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2 or args[0] not in ("login", "run"):
        sys.exit(__doc__)
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 180
    if args[0] == "login":
        login(args[1].lower())
    else:
        run(args[1].lower(), "--apply" in args, limit)
