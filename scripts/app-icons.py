#!/usr/bin/env python3
"""App icons for the news (Kevin, 1 Nov: the site "looks strange just with the letters"; later: "combine them with the
app logos we already have for the thumbnails but still changeable on click bc sometimes the app logos update over time
or sometimes its just the wrong one sounding very similar"). Every app named in a story's "apps" gets a 256 px picture
(img/apps/<slug>.webp) and a colour, both listed in data/app-icons.json. build-pages.js shows them on story cards, the
front page lead and the story pages, so a story without a picture of its own still shows its app.

Where a picture comes from, first match wins:
  1. Kevin's pick in the Studio's Icons tab (studio.useandlike.com/#icons): another App Store app, a logo from the
     thumbnail tool, an uploaded picture, a picture link, or just the letter. This script applies it on the next run.
  2. The thumbnail tool's app library (tngg.app, saved by the editors for the YouTube thumbnails), same name; read only.
  3. The App Store: the app whose name starts with ours, most rated first, if it passes trusted() (2 Nov: same name,
     or name + colon/dash, or the brand's own website or company); else the letter stays and the Icons tab says which
     app looked doubtful. Automatic picks are checked again every run and taken back when they fail.
Every run also looks again at the App Store and the thumbnail tool and takes the new logo when an app changed its own.

    python3 scripts/app-icons.py            # run by the daily news run (NEWS.md step 4), every day
    python3 scripts/app-icons.py --check    # list apps without an icon

Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID for steps 1-2 and the Studio's list; without them it still fetches
App Store icons. data/app-icons.json, one entry per app name as written in "apps", e.g.
    "WhatsApp": {"source": "thumbnails", "tngg": 81, "file": "img/apps/whatsapp.webp", "color": "#25d366", "v": "1a2b3c4d"}
    "Gemini":   {"source": "appstore", "id": 6477489729, "store_name": "Google Gemini", "developer": "Google", ...}
"chosen": true marks Kevin's own pick (never replaced automatically); "none": true leaves a letter on a colour.
"""
import base64, colorsys, hashlib, io, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from collections import Counter

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, "data", "app-icons.json")
NEWS = os.path.join(ROOT, "data", "news")
OUT = os.path.join(ROOT, "img", "apps")
UA = {"User-Agent": "useandlike-site/1.0 (+https://useandlike.com)"}
STUDIO_DB = "8209584b-6109-45f6-9367-5befe0f080a5"   # D1 "useandlike-studio" (useandlike-ops/studio/wrangler.toml)
TNGG_DB = "8a1d7bd6-4b26-401d-8dff-9f3b1a5a4143"     # D1 "tngg-studio": the thumbnail tool's apps (read only)
TNGG_BUCKET = "tngg-studio"                          # its R2 bucket: logos at apps/<id>.png (read only)
# News names that the thumbnail tool saved under another name (normalized: lowercase letters and digits only).
ALIASES = {"chrome": "googlechrome", "googlegemini": "gemini", "excel": "microsoftexcel", "drive": "googledrive",
           "googleonedrive": "onedrive", "microsoftonedrive": "onedrive", "twitter": "x"}
# Short names the news uses for an app the App Store lists under its full name (normalized news name -> store search).
# 2 Nov: "Copilot" alone found "Copilot: Track & Budget Money", a budgeting app; "Outlook" alone found nothing.
STORE_TERMS = {"copilot": "Microsoft Copilot", "outlook": "Microsoft Outlook", "teams": "Microsoft Teams",
               "word": "Microsoft Word", "excel": "Microsoft Excel", "powerpoint": "Microsoft PowerPoint",
               "edge": "Microsoft Edge", "bing": "Microsoft Bing", "onenote": "Microsoft OneNote",
               "gemini": "Google Gemini", "drive": "Google Drive", "maps": "Google Maps", "chrome": "Google Chrome"}


def store_term(name):
    return STORE_TERMS.get(norm(name), name)


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s.replace("+", " plus")).strip("-") or "app"


def norm(name):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower())


# ---------- Cloudflare (the Studio's list and Kevin's picks; the thumbnail tool's library) ----------

def have_cf():
    return bool(os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID"))


def cf(path, body=None, raw=False):
    url = "https://api.cloudflare.com/client/v4/accounts/%s/%s" % (os.environ["CLOUDFLARE_ACCOUNT_ID"], path)
    headers = {"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"]}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, headers)
    for attempt in range(4):
        try:
            r = urllib.request.urlopen(req, timeout=60)
            return r.read() if raw else json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == 3:
                raise
        except urllib.error.URLError:
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)


def d1(db, sql, params=None):
    return cf("d1/database/%s/query" % db, {"sql": sql, "params": params or []})["result"][0]["results"]


def tngg_library():
    """The thumbnail tool's saved apps with a logo: ({normalized name: row}, {id: row}). Combined names ("A & B") are
    only used when Kevin picks one."""
    rows = d1(TNGG_DB, "SELECT id, name, brand_color, source, website FROM apps WHERE logo_key IS NOT NULL")
    return {norm(r["name"]): r for r in rows if "&" not in r["name"] and norm(r["name"])}, {r["id"]: r for r in rows}


def tngg_logo(tid):
    return cf("r2/buckets/%s/objects/apps/%d.png" % (TNGG_BUCKET, int(tid)), raw=True)


# ---------- App Store ----------

def get_json(url):
    for wait in (0, 30, 90):           # Apple's search answers 403 when asked too often: wait and try again
        if wait:
            time.sleep(wait)
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
        except urllib.error.HTTPError as e:
            if e.code not in (403, 429, 503):
                raise
    raise RuntimeError("the App Store keeps refusing: try again later")


def lookup(ids):
    out = {}
    ids = sorted({int(i) for i in ids if i})
    for i in range(0, len(ids), 50):
        part = ids[i:i + 50]
        d = get_json("https://itunes.apple.com/lookup?" + urllib.parse.urlencode({"id": ",".join(map(str, part)), "country": "us"}))
        for r in d.get("results", []):
            out[r["trackId"]] = r
    return out


def trusted(name, app):
    """Whether an App Store app may stand for a name without anyone checking it. 2 Nov: "Codex" had become "Codex Relay -
    Remote Codex App" (one person's side project, 57 ratings), so a store name that only starts the same way isn't enough.
    Yes when the store name is ours ("Siri"), or ours and then a colon, dash or bracket ("Spotify: Music and Podcasts",
    "Eney - AI Assistant"); or the app's website is the brand's own ("Amazon Shopping": amazon.com); or the seller's
    first word is the name's first word ("Meta AI" by Meta Platforms). Otherwise the story keeps the letter, and Kevin
    can pick an icon in the Studio's Icons tab."""
    store = (app.get("trackName") or "").strip()
    if norm(store) == norm(name):
        return True
    low, want = store.lower(), name.lower().strip()
    if low.startswith(want) and low[len(want):].lstrip()[:1] in (":", "-", "–", "—", "|", "(", ","):
        return True
    first = norm(name.split()[0]) if name.split() else ""
    if len(first) < 3:
        return False
    host = (urllib.parse.urlparse(app.get("sellerUrl") or "").hostname or "").split(".")
    site = host[-3] if len(host) >= 3 and host[-2] in ("co", "com", "org", "net") and len(host[-1]) == 2 \
        else (host[-2] if len(host) >= 2 else "")
    if site and norm(site) in (norm(name), first):
        return True
    seller = (app.get("sellerName") or app.get("artistName") or "").split()
    return bool(seller) and norm(seller[0]) == first


def search(name):
    """The App Store app for a name: the most rated one whose name starts with ours and that trusted() accepts.
    Returns (that app or None, the closest app it didn't trust or None)."""
    d = get_json("https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": name, "entity": "software", "country": "us", "limit": 10}))
    want = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    fits = [r for r in d.get("results", [])
            if re.sub(r"[^a-z0-9]+", " ", r["trackName"].lower()).strip().startswith(want)]
    fits.sort(key=lambda r: -(r.get("userRatingCount") or 0))
    for r in fits:
        if trusted(name, r):
            return r, None
    return None, (fits[0] if fits else None)


def doubt_note(app):
    return ("left as a letter: the closest App Store app, %s by %s, may be another app. Pick one here if you know the "
            "right one" % (app.get("trackName"), app.get("artistName") or "an unknown developer"))


def art_url(app):
    return re.sub(r"/\d+x\d+bb\.(jpg|png|webp)$", "/256x256bb.png", app.get("artworkUrl512") or app.get("artworkUrl100") or "")


def download(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()


# ---------- Pictures ----------

def colour(img):
    """The icon's main colour: the most common strong hue (white, black and grey parts left out)."""
    small = img.convert("RGB").resize((40, 40))
    buckets = Counter()
    sums = {}
    raw = small.tobytes()
    for i in range(0, len(raw), 3):
        r, g, b = raw[i], raw[i + 1], raw[i + 2]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l > 0.92 or l < 0.08 or s < 0.25:
            continue
        k = int(h * 24)
        buckets[k] += 1
        t = sums.setdefault(k, [0, 0, 0])
        t[0] += r; t[1] += g; t[2] += b
    if not buckets:
        return "#5b6472"               # grey for black-and-white icons
    k, n = buckets.most_common(1)[0]
    r, g, b = (v / n for v in sums[k])
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    r, g, b = colorsys.hls_to_rgb(h, min(max(l, 0.30), 0.55), min(s, 0.85))   # not too pale, not too dark
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def usable(hexcolour):
    """A brand colour the editors set that works as a background behind the icon (not white, black or grey)."""
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", hexcolour or ""):
        return False
    r, g, b = (int(hexcolour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return s >= 0.3 and 0.2 <= l <= 0.65


def square(img):
    """A 256 px app-icon square. A logo that isn't a full square (a word mark, a round logo with see-through corners)
    goes on a white square with a margin, so every story picture looks like an app icon."""
    img = img.convert("RGBA")
    w, h = img.size
    alpha = img.getchannel("A").resize((64, 64))
    clear = sum(alpha.histogram()[:16]) / (64 * 64)
    if abs(w - h) <= max(w, h) * 0.05 and clear < 0.25:        # an app icon (maybe with rounded, see-through corners)
        out = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
        out.alpha_composite(img.resize((256, 256), Image.LANCZOS))
        return out
    box = img.getbbox() or (0, 0, w, h)
    img = img.crop(box)
    w, h = img.size
    scale = 200 / max(w, h)
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    out = Image.new("RGBA", (256, 256), (255, 255, 255, 255))
    out.alpha_composite(img, ((256 - img.size[0]) // 2, (256 - img.size[1]) // 2))
    return out


def save(name, entry, raw, source, brand=None, **fields):
    img = square(Image.open(io.BytesIO(raw)))
    os.makedirs(OUT, exist_ok=True)
    rel = "img/apps/%s.webp" % slugify(name)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=86, method=6)
    data = buf.getvalue()
    open(os.path.join(ROOT, rel), "wb").write(data)
    for k in ("none", "note", "id", "store_name", "developer", "art", "tngg", "hash", "url", "tngg_skip"):
        entry.pop(k, None)
    entry.update({"source": source, "file": rel, "color": brand if usable(brand) else colour(img),
                  "v": hashlib.sha1(data).hexdigest()[:8]}, **{k: v for k, v in fields.items() if v is not None})


def from_appstore(name, entry, app):
    url = art_url(app)
    if not url:
        return False
    save(name, entry, download(url), "appstore", id=app["trackId"], store_name=app["trackName"],
         developer=app.get("artistName"), art=app.get("artworkUrl512") or app.get("artworkUrl100"))
    return True


def from_tngg(name, entry, row, raw=None):
    raw = raw or tngg_logo(row["id"])
    save(name, entry, raw, "thumbnails", brand=row.get("brand_color"), tngg=row["id"], store_name=row["name"],
         hash=hashlib.sha1(raw).hexdigest()[:12])


def good_tngg(row, raw):
    """Used automatically only when the saved logo is sharp enough and roughly square (not a 48 px favicon or a word mark)."""
    w, h = Image.open(io.BytesIO(raw)).size
    return min(w, h) >= 128 and 0.8 <= w / h <= 1.25


# ---------- Stories ----------

def story_apps():
    """{app name: {"stories": n, "last": newest story date}} in the order they first appear."""
    out = {}
    for f in sorted(os.listdir(NEWS)):
        if f.endswith(".json"):
            s = json.load(open(os.path.join(NEWS, f), encoding="utf-8"))
            for a in s.get("apps") or []:
                if isinstance(a, str) and a.strip():
                    e = out.setdefault(a.strip(), {"stories": 0, "last": ""})
                    e["stories"] += 1
                    e["last"] = max(e["last"], s.get("date") or "")
    return out


def has_file(entry):
    return bool(entry.get("file") and os.path.exists(os.path.join(ROOT, entry["file"])))


# ---------- The run ----------

def main():
    icons = json.load(open(LIST, encoding="utf-8")) if os.path.exists(LIST) else {}
    apps = story_apps()
    for n, e in icons.items():                       # entries from before 2 Nov: App Store pictures
        if e.get("id") and not e.get("source"):
            e["source"] = "appstore"
    if "--check" in sys.argv:
        todo = [n for n in apps if not icons.get(n, {}).get("none") and not has_file(icons.get(n, {}))]
        print("%d apps in stories, %d without an icon: %s" % (len(apps), len(todo), ", ".join(todo) or "none"))
        return

    cf_ok = have_cf()
    picks, library, by_id = {}, {}, {}
    if cf_ok:
        try:
            picks = {r["name"]: (r, json.loads(r["pick"])) for r in
                     d1(STUDIO_DB, "SELECT name, pick, picked_at FROM app_icons WHERE pick IS NOT NULL")}
        except Exception as e:
            print("Could not read Kevin's picks from the Studio (%s); they wait for the next run." % e)
        try:
            library, by_id = tngg_library()
        except Exception as e:
            print("Could not read the thumbnail tool's app library (%s); App Store icons only this time." % e)
    else:
        print("No Cloudflare login in this session: Kevin's picks and the thumbnail tool's logos are skipped this time.")

    changed, applied, failed = [], [], {}

    # 1. Kevin's picks from the Studio's Icons tab.
    for name, (row, pick) in picks.items():
        entry = icons.setdefault(name, {})
        kind = pick.get("kind")
        try:
            if kind == "appstore":
                app = lookup([pick["id"]]).get(int(pick["id"]))
                if not app or not from_appstore(name, entry, app):
                    raise RuntimeError("the App Store has no app %s any more" % pick["id"])
            elif kind == "thumbnails":
                hit = by_id.get(int(pick["id"]))
                if not hit:
                    raise RuntimeError("the thumbnail tool has no logo %s any more" % pick["id"])
                from_tngg(name, entry, hit)
            elif kind == "upload":
                m = re.match(r"data:image/(png|jpeg|webp);base64,(.+)$", pick.get("data") or "", re.S)
                if not m:
                    raise RuntimeError("the uploaded picture can't be read")
                save(name, entry, base64.b64decode(m.group(2)), "upload")
            elif kind == "link":
                save(name, entry, download(pick["url"]), "link", url=pick["url"])
            elif kind == "letter":
                for k in list(entry):
                    entry.pop(k)
                entry.update({"source": "letter", "none": True})
            elif kind == "auto":
                for k in list(entry):
                    entry.pop(k)
            else:
                raise RuntimeError("unknown pick %r" % kind)
            if kind == "auto":
                entry.pop("chosen", None)
            else:
                entry["chosen"] = True
            applied.append((name, row["picked_at"]))
            changed.append("%s (your pick)" % name)
        except Exception as e:
            failed[name] = str(e)
            print("%s: could not apply Kevin's pick: %s" % (name, e))

    # 2a. Automatic App Store picks are checked again every run with trusted() (Kevin, 2 Nov: "find a way to make the
    # corrections of these automatically"): one that fails (picked before the check, or the app was renamed) goes back
    # to the letter, and the Studio's Icons tab says which app it was. Kevin's own picks are never touched.
    auto = {n: e for n, e in icons.items() if e.get("source") == "appstore" and e.get("id") and not e.get("chosen")
            and (e.get("note") or "").startswith("picked automatically")}
    try:
        now = lookup([e["id"] for e in auto.values()]) if auto else {}
    except Exception as e:
        now = {}
        print("Re-check of the automatic App Store icons skipped: %s" % e)
    for name, e in auto.items():
        app = now.get(int(e["id"]))
        if not app or trusted(store_term(name), app):
            continue
        rel = e.get("file")
        for k in list(e):
            e.pop(k)
        e["note"] = doubt_note(app)
        if rel and not any(x.get("file") == rel for x in icons.values()) and os.path.exists(os.path.join(ROOT, rel)):
            os.remove(os.path.join(ROOT, rel))
        print("%s: took back the automatic icon (%s by %s): it may be another app" % (name, app["trackName"], app.get("artistName")))
        changed.append("%s (doubtful icon taken back)" % name)

    # 2. Apps without a picture: the thumbnail tool's logo, else the App Store.
    for name in apps:
        entry = icons.setdefault(name, {})
        if entry.get("chosen") or entry.get("none"):
            continue
        hit = library.get(ALIASES.get(norm(name), norm(name)))
        if hit and entry.get("source") != "thumbnails" and entry.get("tngg_skip") != hit["id"]:
            try:
                raw = tngg_logo(hit["id"])
                if good_tngg(hit, raw):
                    from_tngg(name, entry, hit, raw)
                    changed.append("%s (thumbnail tool)" % name)
                    continue
                entry["tngg_skip"] = hit["id"]         # too small or a word mark: the App Store icon stays
            except Exception as e:
                print("%s: the thumbnail tool's logo could not be read: %s" % (name, e))
        if has_file(entry):
            continue
        app = lookup([entry["id"]]).get(int(entry["id"])) if entry.get("id") else None
        doubt = None
        if not app and not entry.get("id"):
            time.sleep(3)
            app, doubt = search(store_term(name))
            if app:
                print("%s: picked %r by %s (App Store id %s); change it in the Studio's Icons tab if that's the wrong app"
                      % (name, app["trackName"], app.get("artistName"), app["trackId"]))
            elif doubt:
                print("%s: left as a letter: the closest App Store app, %r by %s (%s ratings), may be another app"
                      % (name, doubt["trackName"], doubt.get("artistName"), doubt.get("userRatingCount")))
        if app and from_appstore(name, entry, app):
            entry["note"] = "picked automatically: check it"
            changed.append(name)
        else:
            entry["note"] = doubt_note(doubt) if doubt else \
                "no App Store match: pick one in the Studio's Icons tab, or keep the letter"

    # 3. Logos that changed at the source (an app's new icon, an editor's new logo in the thumbnail tool).
    if "--no-refresh" not in sys.argv:
        stores = {n: e for n, e in icons.items() if e.get("source") == "appstore" and e.get("id") and has_file(e)}
        try:
            known = lookup([e["id"] for e in stores.values()])
        except Exception as e:
            known = {}
            print("App Store refresh skipped: %s" % e)
        for name, e in stores.items():
            app = known.get(int(e["id"]))
            art = app and (app.get("artworkUrl512") or app.get("artworkUrl100"))
            if not art:
                continue
            if not e.get("developer") and app.get("artistName"):
                e["developer"] = app["artistName"]    # entries from before 2 Nov: who made the app, for the Icons tab
            if not e.get("art"):
                e["art"] = art                         # first look: remember it, the picture is from this week
            elif art != e["art"]:
                keep = e.get("chosen"), e.get("note")
                from_appstore(name, e, app)
                if keep[0]:
                    e["chosen"] = True
                if keep[1]:
                    e["note"] = keep[1]
                changed.append("%s (new App Store icon)" % name)
        for name, e in icons.items():
            if e.get("source") != "thumbnails" or not e.get("tngg") or not has_file(e) or not by_id:
                continue
            hit = by_id.get(e["tngg"])
            if not hit:
                continue
            try:
                raw = tngg_logo(hit["id"])
            except Exception:
                continue
            if hashlib.sha1(raw).hexdigest()[:12] != e.get("hash"):
                chosen = e.get("chosen")
                from_tngg(name, e, hit, raw)
                if chosen:
                    e["chosen"] = True
                changed.append("%s (new logo in the thumbnail tool)" % name)

    for e in icons.values():                          # the Icons tab's preview asks for this version of the picture
        if has_file(e) and not e.get("v"):
            e["v"] = hashlib.sha1(open(os.path.join(ROOT, e["file"]), "rb").read()).hexdigest()[:8]

    for name, why in failed.items():
        icons.setdefault(name, {})["pick_error"] = why
    for name, _ in applied:
        icons.get(name, {}).pop("pick_error", None)

    json.dump(dict(sorted(icons.items(), key=lambda kv: kv[0].lower())), open(LIST, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(LIST, "a", encoding="utf-8").write("\n")

    # 4. The Studio's Icons tab shows what the site shows; applied picks are done.
    if cf_ok:
        try:
            sync(icons, apps, applied, failed)
        except Exception as e:
            print("Could not update the Studio's Icons tab: %s" % e)

    missing = [n for n in apps if not has_file(icons.get(n, {})) and not icons.get(n, {}).get("none")]
    print("Icons: %d changed%s; without a picture: %s" % (len(changed), (" (" + ", ".join(changed) + ")") if changed else "",
                                                          ", ".join(missing) or "none"))


def sync(icons, apps, applied, failed):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    cols = ["name", "file", "version", "source", "store_id", "store_name", "developer", "tngg_id", "color", "stories",
            "last_story", "note", "synced_at"]
    rows = []
    for name, a in apps.items():
        e = icons.get(name, {})
        note = ("Couldn't apply your pick: " + failed[name] + ". It tries again on the next run.") if name in failed else e.get("note")
        rows.append([name, e.get("file") if has_file(e) else None, e.get("v"), e.get("source") or ("letter" if e.get("none") else None),
                     e.get("id"), e.get("store_name"), e.get("developer"), e.get("tngg"), e.get("color"), a["stories"],
                     a["last"] or None, note, stamp])
    per = 100 // len(cols)                            # D1 takes at most 100 values per statement
    for i in range(0, len(rows), per):
        part = rows[i:i + per]
        d1(STUDIO_DB, "INSERT INTO app_icons (%s) VALUES %s ON CONFLICT(name) DO UPDATE SET %s" % (
            ", ".join(cols), ", ".join(["(" + ", ".join("?" * len(cols)) + ")"] * len(part)),
            ", ".join("%s = excluded.%s" % (c, c) for c in cols[1:])), [v for r in part for v in r])
    for name, picked_at in applied:                   # a newer pick made during this run stays for the next one
        d1(STUDIO_DB, "UPDATE app_icons SET pick = NULL, picked_at = NULL, picked_by = NULL WHERE name = ? AND picked_at = ?",
           [name, picked_at])
    d1(STUDIO_DB, "DELETE FROM app_icons WHERE pick IS NULL AND (synced_at IS NULL OR synced_at < ?)", [stamp])


if __name__ == "__main__":
    main()
