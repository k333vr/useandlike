#!/usr/bin/env python3
"""App icons for the news (Kevin, 1 Nov: the site "looks strange just with the letters"): every app named in a story's
"apps" gets its App Store icon (img/apps/<slug>.webp, 256 px) and a colour taken from the icon, both listed in
data/app-icons.json. build-pages.js shows them on story cards, the front page lead and the story pages, so a story
without a picture of its own still shows its app. The icons are the apps' own (they name the app in our coverage).

    python3 scripts/app-icons.py            # icons for apps that don't have one yet (run by the daily news run)
    python3 scripts/app-icons.py --check    # list apps without an icon

data/app-icons.json, one entry per app name as written in "apps":
    "WhatsApp": {"id": 310633997, "file": "img/apps/whatsapp.webp", "color": "#25d366"}
A new name is looked up in the App Store; the result is used only when its name starts with the app's name (e.g.
"WhatsApp Messenger" for WhatsApp). Pick by hand when that fails or picks the wrong app: put the App Store id in
"id" (from the app's apps.apple.com address) and run the script again; "none": true leaves a letter on a colour.
"""
import colorsys, io, json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from collections import Counter

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, "data", "app-icons.json")
NEWS = os.path.join(ROOT, "data", "news")
OUT = os.path.join(ROOT, "img", "apps")
UA = {"User-Agent": "useandlike-site/1.0 (+https://useandlike.com)"}


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s.replace("+", " plus")).strip("-") or "app"


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
    for i in range(0, len(ids), 50):
        part = ids[i:i + 50]
        d = get_json("https://itunes.apple.com/lookup?" + urllib.parse.urlencode({"id": ",".join(map(str, part)), "country": "us"}))
        for r in d.get("results", []):
            out[r["trackId"]] = r
    return out


def search(name):
    """The App Store app whose name starts with ours, most rated first (None when nothing fits)."""
    d = get_json("https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": name, "entity": "software", "country": "us", "limit": 10}))
    want = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    fits = [r for r in d.get("results", [])
            if re.sub(r"[^a-z0-9]+", " ", r["trackName"].lower()).strip().startswith(want)]
    fits.sort(key=lambda r: -(r.get("userRatingCount") or 0))
    return fits[0] if fits else None


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


def save_icon(name, entry, app):
    url = re.sub(r"/\d+x\d+bb\.(jpg|png|webp)$", "/256x256bb.png", app.get("artworkUrl512") or app.get("artworkUrl100") or "")
    if not url:
        return False
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
    img = Image.open(io.BytesIO(raw)).convert("RGBA").resize((256, 256), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    rel = "img/apps/%s.webp" % slugify(name)
    img.save(os.path.join(ROOT, rel), "WEBP", quality=86, method=6)
    entry.update({"id": app["trackId"], "file": rel, "color": colour(img), "store_name": app["trackName"]})
    return True


def story_apps():
    names = []
    for f in sorted(os.listdir(NEWS)):
        if f.endswith(".json"):
            for a in json.load(open(os.path.join(NEWS, f), encoding="utf-8")).get("apps") or []:
                if isinstance(a, str) and a.strip() and a not in names:
                    names.append(a.strip())
    return names


def main():
    icons = json.load(open(LIST, encoding="utf-8")) if os.path.exists(LIST) else {}
    names = story_apps()
    todo = [n for n in names if not icons.get(n, {}).get("none")
            and not (icons.get(n, {}).get("file") and os.path.exists(os.path.join(ROOT, icons[n]["file"])))]
    if "--check" in sys.argv:
        print("%d apps in stories, %d without an icon: %s" % (len(names), len(todo), ", ".join(todo) or "none"))
        return
    known = lookup([icons[n]["id"] for n in todo if icons.get(n, {}).get("id")])
    done, missing = 0, []
    for n in todo:
        entry = icons.setdefault(n, {})
        app = known.get(entry.get("id"))
        if not app and not entry.get("id"):
            time.sleep(3)
            app = search(n)
            if app:
                print("%s: picked %r (App Store id %s); set another id in data/app-icons.json if that's the wrong app"
                      % (n, app["trackName"], app["trackId"]))
        if app and save_icon(n, entry, app):
            done += 1
        else:
            missing.append(n)
            entry.setdefault("note", "no App Store match: add an id, or \"none\": true for a letter")
    json.dump(dict(sorted(icons.items(), key=lambda kv: kv[0].lower())), open(LIST, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(LIST, "a", encoding="utf-8").write("\n")
    print("%d new icons; without one: %s" % (done, ", ".join(missing) or "none"))


if __name__ == "__main__":
    main()
