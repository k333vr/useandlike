#!/usr/bin/env python3
"""Builds the lists the video editors use for descriptions.

Output (folder editors/, not published on the site):
  tool-links.csv          every tool with its short link
  videos-<channel>.csv    each channel's videos (Shorts left out), most viewed first, with the exact lines to paste
                          (How To Rocket and Guide Glimpse; Logic Protocol's uploads are music remixes, left out)
Run after changing TOOLS, _redirects or the cancel guides: python3 scripts/build-editor-lists.py
Needs data/channel-videos.tsv (scripts/fetch-videos.sh) and the subscriptionchef repo next to this one (for cancel guides).
"""
import csv, importlib.util, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
spec = importlib.util.spec_from_file_location("bv", os.path.join(ROOT, "scripts", "build-videos.py"))
bv = importlib.util.module_from_spec(spec); spec.loader.exec_module(bv)

NEWSLETTER_LINE = "📩 Join Our Newsletter & Get Free Subscription Tracker: useandlike.com/join"
CANCEL = re.compile(r"\bcancel|unsubscribe|end (your |my )?(membership|subscription)|stop (your |my )?subscription", re.I)
# Extra ways a cancel guide's service is written in titles.
GUIDE_ALIASES = {
    "disney-plus": ["disney plus", "disney+"], "paramount-plus": ["paramount plus", "paramount+"],
    "youtube-tv": ["youtube tv"], "hbo-max": ["hbo max"], "apple-tv": ["apple tv"], "espn": ["espn"],
    "sling-tv": ["sling"], "microsoft-365": ["microsoft 365", "office 365"], "xbox-game-pass": ["game pass"],
    "playstation-plus": ["playstation plus", "ps plus"], "icloud": ["icloud"], "siriusxm": ["siriusxm", "sirius xm"],
    "hellofresh": ["hellofresh", "hello fresh"], "linkedin-premium": ["linkedin"], "youtube-premium": ["youtube premium"],
    "amazon-music": ["amazon music"], "amazon-prime": ["amazon prime", "prime membership", "prime video"],
    "kindle-unlimited": ["kindle unlimited"], "chatgpt": ["chatgpt"], "spotify": ["spotify"], "canva": ["canva"],
    "roku": ["roku"], "iphone-subscriptions": ["iphone", "app store subscription"], "factor": ["factor meals", "factor 75", "factor"],
}


def load_tools():
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    return bv.read_js_array(src, "TOOLS")


def make_matcher(tools):
    """Returns lines_for(title) -> (kind, [lines to put at the top of the description])."""
    slug_of = {t["name"]: t["slug"] for t in tools}
    guides = []
    gpath = os.path.join(ROOT, "..", "subscriptionchef", "tools")
    if os.path.isdir(gpath):
        sys.path.insert(0, gpath)
        import guides as gmod
        for g in gmod.GUIDES:
            keys = GUIDE_ALIASES.get(g["slug"], [g["name"].lower().replace("+", "")])
            guides += [(k, g["slug"]) for k in keys]
    guides.sort(key=lambda k: -len(k[0]))
    gpat = [(re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])"), s) for k, s in guides]
    keys = [(k, t["name"]) for t in tools for k in bv.ALIASES.get(t["name"], [t["name"].lower()])]
    keys.sort(key=lambda k: -len(k[0]))
    tpat = [(re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])"), n) for k, n in keys]

    def lines_for(title):
        tl = " " + title.lower() + " "
        if CANCEL.search(title):
            g = next((s for rx, s in gpat if rx.search(tl)), None)
            if g:
                return "cancel guide", ["👉 Step-by-step guide: subscriptionchef.app/cancel/" + g, NEWSLETTER_LINE]
        elif not bv.EXCLUDE.search(title):
            tool = next((n for rx, n in tpat if rx.search(tl)), None)
            if tool:
                return "tool", ["👉 Try %s (affiliate link): useandlike.com/%s" % (tool, slug_of[tool]), NEWSLETTER_LINE]
        return "newsletter only", [NEWSLETTER_LINE]
    return lines_for


def main():
    tools = load_tools()
    os.makedirs(os.path.join(ROOT, "editors"), exist_ok=True)

    with open(os.path.join(ROOT, "editors", "tool-links.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Tool", "Category", "Link for descriptions"])
        for t in sorted(tools, key=lambda t: (t["category"], t["name"].lower())):
            w.writerow([t["name"], t["category"], "useandlike.com/" + t["slug"]])

    lines_for = make_matcher(tools)
    rows, seen = [], set()
    for line in open(os.path.join(ROOT, "data", "channel-videos.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 5 or p[0] in seen:
            continue
        vid, views, secs, title, channel = p[:5]
        seen.add(vid)
        try:
            if 0 < float(secs) <= 60:
                continue
        except ValueError:
            pass
        kind, lines = lines_for(title)
        rows.append((int(views) if views.isdigit() else 0, channel, title, "https://youtu.be/" + vid, kind, "\n".join(lines)))
    rows.sort(key=lambda r: -r[0])

    for channel in ("How To Rocket", "Guide Glimpse"):
        name = "videos-" + channel.lower().replace(" ", "-") + ".csv"
        with open(os.path.join(ROOT, "editors", name), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Views", "Video title", "Video link", "Type", "Paste at the top of the description"])
            w.writerows([r[0], r[2], r[3], r[4], r[5]] for r in rows if r[1] == channel)
    count = {}
    for r in rows:
        if r[1] == "Logic Protocol":
            continue
        count[r[4]] = count.get(r[4], 0) + 1
    print(len(tools), "tools,", len(rows), "videos:", count)


if __name__ == "__main__":
    main()
