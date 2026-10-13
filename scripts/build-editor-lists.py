#!/usr/bin/env python3
"""Builds the lists the video editors use for descriptions.

Output (folder editors/, not published on the site):
  tool-links.csv          every tool with its short link
And outside editors/: team-links/index.html, the same links as a hidden page on the site for the manager and
uploaders (LINKS_PAGE_URL: not linked anywhere, noindex, not in the sitemap): a Copy button for each 👉 line, the date
each link was added (from git), what's new and what was removed, and a box that turns a new video's title into the
pinned comment (a question + the 👉 line + the newsletter line) and the description lines, with the same title rules as
below (Kevin, 13 Oct: "a box where the editor or manager can add the video title and gets also the question for the
pinned comment"). It goes live with the next push to main.
  videos-<channel>.csv    each channel's videos (Shorts left out), most viewed first, with the exact lines to paste
                          (How To Rocket and Guide Glimpse; Logic Protocol's uploads are music remixes, left out)
Run after changing TOOLS, _redirects or the cancel guides: python3 scripts/build-editor-lists.py
Needs data/channel-videos.tsv (scripts/fetch-videos.sh) and the subscriptionchef repo next to this one (for cancel guides).
"""
import csv, html, importlib.util, json, os, re, subprocess, sys, urllib.parse
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
spec = importlib.util.spec_from_file_location("bv", os.path.join(ROOT, "scripts", "build-videos.py"))
bv = importlib.util.module_from_spec(spec); spec.loader.exec_module(bv)

NEWSLETTER_LINE = "📩 Join Our Newsletter & Get Free Subscription Tracker: useandlike.com/join"
# Tool names that YouTube would turn into a link to the brand's own site (without our affiliate code): shorter name
# in the 👉 line. (Systeme.io predates this list; its line is already on many videos.)
LINE_NAME = {"Booking.com": "Booking", "Kiwi.com": "Kiwi", "lastminute.com": "lastminute"}
# Team links page (affiliate-links.html).
LINKS_PAGE_URL = "https://useandlike.com/team-links/"  # hidden page (Kevin, 13 Oct: "no hustle to share")
OWN_HOSTS = ("useandlike.com", "useandlike.beehiiv.com", "subscriptionchef.app")  # our own short links, left off the page
# Names and groups of the short links that aren't tools on the site (most written by useandlike-ops/analysis/yazing-add.py).
SHORT_LINKS = os.path.join(ROOT, "data", "short-links.json")
# Last line of a pinned comment (the description uses NEWSLETTER_LINE); same as useandlike-ops/analysis/pinned-comment-lines.py.
PINNED_NEWS = "📩 Free Subscription Tracker + new app tips by email: useandlike.com/join"
# Link-only names that are ordinary words: the page's "new video" box doesn't pick them from a title by itself.
NO_AUTO = {"box", "changed", "rover", "knack", "reverb", "lot", "empower", "parallels", "pigment", "condor", "optimum",
           "acorns", "carla"}
NEW_DAYS = 7  # "New" badge
NEWS_DAYS = 30  # how far back "What's new" and "Removed" look
FOLD = 40  # a day in "What's new" with more than FOLD + 10 new links shows the rest behind "N more"
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


def cancel_guides():
    """subscriptionchef.app's cancel guides: [(slug, name, [ways the title writes it])] (empty without that repo)."""
    gpath = os.path.join(ROOT, "..", "subscriptionchef", "tools")
    if not os.path.isdir(gpath):
        return []
    sys.path.insert(0, gpath)
    import guides as gmod
    return [(g["slug"], g["name"], GUIDE_ALIASES.get(g["slug"], [g["name"].lower().replace("+", "")])) for g in gmod.GUIDES]


def make_matcher(tools):
    """Returns lines_for(title) -> (kind, [lines to put at the top of the description])."""
    slug_of = {t["name"]: t["slug"] for t in tools}
    guides = [(k, slug) for slug, _, keys in cancel_guides() for k in keys]
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
            # Same "other product with the same name" rule as the site (bv.NOT_ABOUT): no Wise link on Wise Care videos.
            tool = next((n for rx, n in tpat if rx.search(tl) and not (n in bv.NOT_ABOUT and bv.NOT_ABOUT[n].search(title))), None)
            if tool:
                return "tool", ["👉 Try %s (affiliate): useandlike.com/%s" % (LINE_NAME.get(tool, tool), slug_of[tool]), NEWSLETTER_LINE]
        return "newsletter only", [NEWSLETTER_LINE]
    return lines_for


def link_history():
    """From git: slug -> day it first appeared in _redirects, and slug -> day it was taken out (for links now gone)."""
    git = lambda *a: subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True, check=True).stdout
    added, removed, prev = {}, {}, set()
    for line in git("log", "--reverse", "--format=%H %as", "--", "_redirects").splitlines():
        sha, day = line.split()
        now = set(re.findall(r"^/([\w-]+)\s+\S+", git("show", sha + ":_redirects"), re.M))
        for s in now - prev:
            added.setdefault(s, day)
            removed.pop(s, None)
        for s in prev - now:
            removed[s] = day
        prev = now
    return added, removed


def nice_day(day):
    d = date.fromisoformat(day)
    return "%d %s" % (d.day, d.strftime("%b %Y"))


def write_links_page(tools):
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    order = bv.read_js_array(src, "CATEGORIES")
    redirects = re.findall(r"^/([\w-]+)\s+(\S+)", open(os.path.join(ROOT, "_redirects"), encoding="utf-8").read(), re.M)
    added, removed = link_history()
    today = date.today()
    by_slug = {t["slug"]: t for t in tools}
    extra = json.load(open(SHORT_LINKS, encoding="utf-8")) if os.path.exists(SHORT_LINKS) else {}
    links = []
    for slug, target in redirects:
        if (urllib.parse.urlparse(target).hostname or "").endswith(OWN_HOSTS):
            continue
        t, x = by_slug.get(slug), extra.get(slug, {})
        if not t and not x:
            print("WARN: /%s is a short link without a tool or a name: add it to data/short-links.json" % slug)
        name = t["name"] if t else x.get("name", slug)
        written = LINE_NAME.get(name, name) if t else x.get("line_name", name)
        links.append({"slug": slug, "name": name, "cat": t["category"] if t else x.get("group", "Other"), "written": written,
                      "line": "👉 Try %s (affiliate): useandlike.com/%s" % (written, slug),
                      "added": added.get(slug, today.isoformat())})  # not committed yet: today
    esc = lambda s: html.escape(s, quote=True)

    def row(l):
        note = ""
        if l["written"] != l["name"]:
            note = ('<p class="note">Written as “%s” on purpose: YouTube would turn “%s” into a direct link without our '
                    'code.</p>' % (esc(l["written"]), esc(l["name"])))
        new = (today - date.fromisoformat(l["added"])).days < NEW_DAYS
        return ('<div class="row" id="l-{slug}" data-line="{line}" data-q="{q}" data-added="{iso}"><div class="who"><span class="name">{name}'
                '</span>{badge}<span class="date">Added {day}</span></div><code class="line">{line}</code><button '
                'type="button" data-copy aria-label="Copy the line for {name}">Copy</button>{note}</div>\n').format(
            slug=esc(l["slug"]), line=esc(l["line"]), name=esc(l["name"]), note=note, day=nice_day(l["added"]), iso=l["added"],
            q=esc(" ".join([l["name"], l["slug"], l["cat"]]).lower()), badge='<span class="badge">New</span>' if new else "")

    sections = []
    for c in order + sorted({l["cat"] for l in links} - set(order), key=lambda c: (c == "Other", c)):
        rows = sorted((l for l in links if l["cat"] == c), key=lambda l: l["name"].lower())
        if rows:
            sections.append('<section class="cat"><h2>%s <span>%d</span></h2>\n%s</section>\n' % (esc(c), len(rows), "".join(map(row, rows))))
    cutoff = (today - timedelta(days=NEWS_DAYS)).isoformat()
    start = min(added.values(), default="")  # the site's first links aren't news
    news = []
    for d in sorted({l["added"] for l in links if l["added"] >= cutoff and l["added"] != start}, reverse=True)[:3]:
        items = sorted((l for l in links if l["added"] == d), key=lambda l: l["name"].lower())
        chips = ['<a href="#l-%s" data-jump="%s">%s</a>' % (esc(l["slug"]), esc(l["slug"]), esc(l["name"])) for l in items]
        more = ('<details class="more"><summary>%d more</summary><p class="chips">%s</p></details>' % (
            len(chips) - FOLD, "".join(chips[FOLD:]))) if len(chips) > FOLD + 10 else ""
        news.append('<div class="day"><h3>%s <span>%d %s</span></h3><p class="chips">%s</p>%s</div>\n' % (
            nice_day(d), len(items), "link" if len(items) == 1 else "links", "".join(chips[:FOLD] if more else chips), more))
    live = {l["slug"] for l in links}
    gone = sorted(((s, d) for s, d in removed.items() if d >= cutoff and s not in live), key=lambda x: x[1], reverse=True)
    if gone:
        news.append('<div class="gone"><h3>Removed: don’t use these any more</h3><ul>%s</ul></div>\n' % "".join(
            '<li><code>useandlike.com/%s</code> taken out %s</li>' % (esc(s), nice_day(d)) for s, d in gone))
    # The "new video" box: the same title rules as make_matcher (aliases, other products with the same name, no affiliate
    # line on cancel/refund/free videos), over every link on the page (link-only ones by their name).
    items = []
    for l in sorted(links, key=lambda l: l["name"].lower()):
        if l["slug"] in by_slug:
            k, x = bv.ALIASES.get(l["name"], [l["name"].lower()]), bv.NOT_ABOUT.get(l["name"])
        else:
            n = l["name"].lower()
            k, x = ([] if n in NO_AUTO else [n]), None
            first = (re.findall(r"[a-z0-9]+", n) or [""])[0]
            if k and " " in n and first == l["slug"] and len(first) >= 5:   # "CyberGhost VPN" also as "cyberghost"
                k.append(first)
        items.append({"s": l["slug"], "n": l["name"], "w": l["written"], "k": k, "x": x.pattern if x else ""})
    box = {"items": items, "guides": [{"s": s, "n": n, "k": k} for s, n, k in cancel_guides()],
           "exclude": bv.EXCLUDE.pattern, "cancel": CANCEL.pattern, "suffix": bv.SUFFIX.pattern, "pinNews": PINNED_NEWS}
    page = (LINKS_TEMPLATE.replace("/*BOX_JS*/", BOX_JS).replace("/*BOX*/", json.dumps(box, ensure_ascii=False).replace("</", "<\\/"))
            .replace("<!--COUNT-->", str(len(links))).replace("<!--UPDATED-->", nice_day(today.isoformat()))
            .replace("<!--NEWSLETTER-->", esc(NEWSLETTER_LINE)).replace("/*NEWSLETTER*/", json.dumps(NEWSLETTER_LINE))
            .replace("<!--NEW_DAYS-->", str(NEW_DAYS)).replace("/*NEW_DAYS*/", str(NEW_DAYS))
            .replace("<!--NEWS-->", "".join(news)).replace("<!--LIST-->", "".join(sections)))
    icon = re.search(r'<link rel="icon"[^>]*>', src)
    page = page.replace("<!--ICON-->", icon.group(0) if icon else "")
    os.makedirs(os.path.join(ROOT, "team-links"), exist_ok=True)
    with open(os.path.join(ROOT, "team-links", "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    return len(links)


LINKS_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>useandlike Affiliate Links</title>
<!--ICON-->
<style>
[hidden] { display: none !important; }
:root {
  /* Layout: one ledger column like useandlike.com: a sticky finder bar, a What's-new note, then one row per link
     under its category, each with the exact line to paste and a Copy button. Colors and faces are the site's own. */
  --bg: #fbfaf7; --surface: #ffffff; --text: #1a1c20; --muted: #585d66; --line: #dcd7cc;
  --brand: #1f3a5f; --brand-text: #ffffff; --brass: #9a7428; --link: #1f4f8f; --soft: #f0ede6;
  --ok: #2d6a4f; --new-bg: #f5ead2; --new-fg: #6f5216; --flash: #f8edcf;
  --serif: Georgia, "Times New Roman", serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #121417; --surface: #191c21; --text: #ebe9e4; --muted: #a7abb3; --line: #2e333b;
    --brand: #a9c2e6; --brand-text: #121417; --brass: #d4b06a; --link: #a6c3f5; --soft: #1d2127;
    --ok: #8fd1ae; --new-bg: #2e2719; --new-fg: #e2c38a; --flash: #2b2618; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #121417; --surface: #191c21; --text: #ebe9e4; --muted: #a7abb3; --line: #2e333b;
  --brand: #a9c2e6; --brand-text: #121417; --brass: #d4b06a; --link: #a6c3f5; --soft: #1d2127;
  --ok: #8fd1ae; --new-bg: #2e2719; --new-fg: #e2c38a; --flash: #2b2618; color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 16px/1.5 var(--sans); }
.wrap { max-width: 980px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 48px; }
.eyebrow { margin: 0; font-size: .78rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--brass); }
h1 { font-family: var(--serif); font-weight: 400; font-size: clamp(1.9rem, 5vw, 2.5rem); line-height: 1.15; margin: .3rem 0 .6rem; color: var(--brand); text-wrap: balance; }
.lede { margin: 0; max-width: 64ch; }
.meta { margin: .6rem 0 0; font-size: .9rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.bar { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 2; background: var(--bg); border-bottom: 1px solid var(--line);
  margin-top: 18px; padding-block: 12px; display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: center; }
#q { flex: 1 1 260px; min-width: 0; font: inherit; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--text); }
.opt { display: flex; gap: 8px; align-items: center; cursor: pointer; }
.opt em { font-style: normal; color: var(--muted); }
.nl-line { margin: .35rem 0 0; font-size: .8rem; color: var(--muted); overflow-wrap: anywhere; }
code { font-family: var(--mono); }
.news { margin-top: 22px; padding: 16px 18px; background: var(--soft); border-radius: 10px; display: grid; gap: 14px; }
.news h2 { font-family: var(--serif); font-weight: 400; font-size: 1.35rem; margin: 0; }
.day h3, .gone h3 { margin: 0 0 6px; font-size: .95rem; font-weight: 600; }
.day h3 span, .cat h2 span { font-weight: 400; color: var(--muted); font-variant-numeric: tabular-nums; }
.chips { margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.chips a { color: var(--link); text-decoration: none; background: var(--surface); border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px; font-size: .88rem; }
.chips a:hover { border-color: var(--link); }
.more summary { margin-top: 6px; cursor: pointer; color: var(--link); font-size: .88rem; }
.more .chips { margin-top: 6px; }
.gone ul { margin: 0; padding-left: 18px; }
.cat { margin-top: 30px; }
.cat h2 { font-family: var(--serif); font-weight: 400; font-size: 1.3rem; margin: 0; padding-bottom: 6px; border-bottom: 2px solid var(--brand); }
.row { display: grid; grid-template-columns: minmax(9rem, 14rem) minmax(0, 1fr) auto; gap: 6px 16px; align-items: center; padding: 10px 6px; border-bottom: 1px solid var(--line); }
.who { display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 8px; min-width: 0; }
.name { font-weight: 600; }
.badge { font-size: .7rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; background: var(--new-bg); color: var(--new-fg); border-radius: 4px; padding: 1px 6px; }
.date { flex-basis: 100%; font-size: .8rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.line { font-size: .88rem; min-width: 0; overflow-wrap: anywhere; }
button[data-copy], button[data-copyout] { font: inherit; font-size: .9rem; font-weight: 600; min-width: 6.8rem; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--brand); background: var(--brand); color: var(--brand-text); cursor: pointer; }
button[data-copy]:hover, button[data-copyout]:hover { filter: brightness(1.12); }
button[data-copy].ok, button[data-copyout].ok { background: var(--surface); color: var(--ok); border-color: var(--ok); }
.maker { margin-top: 20px; padding: 16px 18px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); display: grid; gap: 10px; }
.maker h2 { font-family: var(--serif); font-weight: 400; font-size: 1.35rem; margin: 0; }
.maker .hint { margin: 0; max-width: 70ch; font-size: .9rem; color: var(--muted); }
.field, .pickrow label, .outhead span { font-size: .9rem; font-weight: 600; }
#vt, #vtool, .out textarea { font: inherit; width: 100%; min-width: 0; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--text); }
#made { display: grid; gap: 12px; }
.pickrow { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }
#vtool { width: auto; max-width: 100%; flex: 0 1 22rem; }
.vnote { font-size: .85rem; color: var(--muted); }
.out { display: grid; gap: 6px; }
.outhead { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.out textarea { font-family: var(--mono); font-size: .86rem; line-height: 1.45; resize: vertical; }
:focus-visible { outline: 3px solid var(--brass); outline-offset: 2px; }
.note { grid-column: 2 / -1; margin: 0; font-size: .8rem; color: var(--muted); }
.row.flash { background: var(--flash); }
.none { margin-top: 24px; padding: 14px 16px; border: 1px dashed var(--line); border-radius: 10px; color: var(--muted); }
footer { margin-top: 36px; max-width: 70ch; font-size: .85rem; color: var(--muted); }
@media (max-width: 640px) {
  .row { grid-template-columns: minmax(0, 1fr) auto; }
  .who { grid-column: 1; grid-row: 1; }
  button[data-copy] { grid-column: 2; grid-row: 1; min-width: 5.6rem; }
  .line, .note { grid-column: 1 / -1; }
}
@media (prefers-reduced-motion: no-preference) { .row { transition: background-color .6s; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <p class="eyebrow">useandlike.com · for the manager and uploaders</p>
    <h1>Affiliate links</h1>
    <p class="lede">Find the tool a video is about, press Copy and paste the line at the very top of the description or
      into the pinned comment. Use only these short links. A video about an app that isn’t listed gets only the newsletter line.</p>
    <p class="meta"><b><!--COUNT--></b> links · updated <!--UPDATED--></p>
    <p class="nl-line">Newsletter line, added when you tick the box below: <code><!--NEWSLETTER--></code></p>
  </header>

  <section class="maker" aria-labelledby="maker-h">
    <h2 id="maker-h">New video? Paste its title</h2>
    <p class="hint">You get the pinned comment (a question that invites replies, the 👉 line and the newsletter line) and the
      lines for the top of the description. Check the link and the question, change them if needed, then copy.</p>
    <label class="field" for="vt">Video title</label>
    <input id="vt" type="text" autocomplete="off" placeholder="e.g. How to Book a Flight Ticket on Kiwi.com">
    <div id="made" hidden>
      <div class="pickrow"><label for="vtool">Link</label><select id="vtool"></select><span id="vnote" class="vnote"></span></div>
      <div class="out"><div class="outhead"><span>Pinned comment</span><button type="button" data-copyout="pin">Copy</button></div>
        <textarea id="pin" rows="4" spellcheck="false" aria-label="Pinned comment"></textarea></div>
      <div class="out"><div class="outhead"><span>Top of the description</span><button type="button" data-copyout="desc">Copy</button></div>
        <textarea id="desc" rows="3" spellcheck="false" aria-label="Top of the description"></textarea></div>
    </div>
  </section>

  <div class="bar">
    <input id="q" type="search" placeholder="Find a tool, e.g. Wise" aria-label="Find a tool" autocomplete="off">
    <label class="opt" for="nl"><input id="nl" type="checkbox"><span>Copy with the newsletter line <em>(for descriptions)</em></span></label>
    <label class="opt" for="onlynew"><input id="onlynew" type="checkbox"><span>Only new <em>(last <!--NEW_DAYS--> days)</em></span></label>
  </div>

  <section id="news" class="news" aria-label="What's new">
    <h2>What’s new</h2>
<!--NEWS-->  </section>

  <p id="none" class="none" hidden></p>

  <div id="list">
<!--LIST-->  </div>

  <footer>This page is rebuilt from the site’s link list whenever a link is added or taken out. A line you already pasted
    keeps working unless its link is listed under Removed.</footer>
</div>

<script>
(function () {
  var NEWS = /*NEWSLETTER*/, NEW_DAYS = /*NEW_DAYS*/;
  var q = document.getElementById("q"), nl = document.getElementById("nl"), only = document.getElementById("onlynew");
  // "New" is set when the page is built; take it off links older than NEW_DAYS by now (the page may not be rebuilt for a while).
  var today = new Date(); today.setHours(0, 0, 0, 0);
  document.querySelectorAll("#list .row").forEach(function (r) {
    var b = r.querySelector(".badge");
    if (b && (today - new Date(r.dataset.added + "T00:00:00")) / 864e5 >= NEW_DAYS) b.remove();
  });
  try { nl.checked = localStorage.getItem("team-links-newsletter") === "1"; } catch (e) {}
  nl.addEventListener("change", function () {
    try { localStorage.setItem("team-links-newsletter", nl.checked ? "1" : "0"); } catch (e) {}
  });

  function flashButton(b, text, ok) {
    b.textContent = text;
    b.classList.toggle("ok", ok);
    setTimeout(function () { b.textContent = "Copy"; b.classList.remove("ok"); }, 1800);
  }
  function selectLine(row) {
    var r = document.createRange();
    r.selectNodeContents(row.querySelector(".line"));
    var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  }
  function oldCopy(text) {
    var t = document.createElement("textarea");
    t.value = text; t.setAttribute("readonly", ""); t.style.position = "fixed"; t.style.top = "0"; t.style.opacity = "0";
    document.body.appendChild(t); t.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(t);
    return ok;
  }
  function copyText(text, b, onFail) {
    var fallback = function () {
      if (oldCopy(text)) { flashButton(b, "Copied ✓", true); return; }
      onFail(); flashButton(b, "Press Ctrl+C", false);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flashButton(b, "Copied ✓", true); }, fallback);
    } else { fallback(); }
  }
  function copy(b) {
    var row = b.closest(".row");
    copyText(row.dataset.line + (nl.checked ? "\\n" + NEWS : ""), b, function () { selectLine(row); });
  }
/*BOX_JS*/
  function filter() {
    var s = q.value.trim().toLowerCase(), o = only.checked, shown = 0;
    document.querySelectorAll("#list .row").forEach(function (r) {
      var hit = (!s || r.dataset.q.indexOf(s) !== -1) && (!o || !!r.querySelector(".badge"));
      r.hidden = !hit; if (hit) shown++;
    });
    document.querySelectorAll("#list .cat").forEach(function (c) { c.hidden = !c.querySelector(".row:not([hidden])"); });
    document.getElementById("news").hidden = !!s || o;
    var none = document.getElementById("none");
    none.textContent = s ? "No link for “" + q.value.trim() + "”" + (o ? " among the new ones." : ". A video about it gets only the newsletter line.")
      : "No links were added in the last " + NEW_DAYS + " days.";
    none.hidden = shown > 0;
  }
  function jump(slug) {
    if (q.value || only.checked) { q.value = ""; only.checked = false; filter(); }
    var r = document.getElementById("l-" + slug);
    if (!r) return;
    var still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    r.scrollIntoView({ block: "center", behavior: still ? "auto" : "smooth" });
    r.classList.add("flash");
    setTimeout(function () { r.classList.remove("flash"); }, 1800);
  }
  q.addEventListener("input", filter);
  only.addEventListener("change", filter);
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-copy]");
    if (b) { copy(b); return; }
    var o = ev.target.closest("button[data-copyout]");
    if (o) { var ta = document.getElementById(o.dataset.copyout); copyText(ta.value, o, function () { ta.focus(); ta.select(); }); return; }
    var a = ev.target.closest("a[data-jump]");
    if (a) { ev.preventDefault(); jump(a.dataset.jump); }
  });
})();
</script>
</body>
</html>
"""


# The page's "new video" box (inserted at /*BOX_JS*/; a raw string, so its regular expressions stay as written).
BOX_JS = r"""  // New video box: title -> pinned comment and the lines for the description (same rules as the editor lists).
  var BOX = /*BOX*/;
  var EXCLUDE = new RegExp(BOX.exclude, "i"), CANCEL = new RegExp(BOX.cancel, "i"), SUFFIX = new RegExp(BOX.suffix, "i");
  var reEsc = function (s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); };
  var word = function (k) { return new RegExp("[^a-z0-9]" + reEsc(k) + "[^a-z0-9]"); };
  var keys = [], gkeys = [], bySlug = {};
  BOX.items.forEach(function (it) {
    bySlug[it.s] = it;
    if (it.x) it.xr = new RegExp(it.x, "i");
    it.k.forEach(function (k) { keys.push({ k: k, it: it, rx: word(k) }); });
  });
  BOX.guides.forEach(function (g) { g.k.forEach(function (k) { gkeys.push({ k: k, g: g, rx: word(k) }); }); });
  keys.sort(function (a, b) { return b.k.length - a.k.length; });
  gkeys.sort(function (a, b) { return b.k.length - a.k.length; });

  // Words that are lowercase in a sentence ("How To Book Flight Ticket" -> "book flight ticket"); names keep their capitals.
  var COMMON = {};
  ("a an and or the to in on at of for from with by into onto over your my our their his her its this that these those it you " +
   "we they me him them i use using make create add remove delete change edit rename set setup get find fix turn off enable " +
   "disable install uninstall download upload update open close start stop share send receive transfer book order buy sell pay " +
   "cancel unsubscribe sign log login logout out back check see watch play join leave hide show block unblock connect disconnect " +
   "link unlink verify activate deactivate reset recover restore backup save print scan convert merge split crop cut trim rotate " +
   "resize compress translate write read apply claim redeem earn withdraw deposit top load register renew track search schedule " +
   "move copy paste import export sync stream cast mirror record take go run try put keep call text post like follow unfollow " +
   "invite accept reply pin unpin mute unmute archive lock unlock clear free new old account accounts app apps phone mobile android " +
   "iphone ipad pc laptop computer windows mac browser video videos photo photos picture pictures image images screen chat chats " +
   "message messages data file files folder folders password passwords email emails mail number numbers card cards money payment " +
   "payments ticket tickets flight flights hotel hotels room rooms trip trips car cars game games mod mods version language " +
   "languages name profile settings setting notification notifications status story stories group groups page pages channel " +
   "channels links website site online offline wifi internet network storage space cloud drive music song songs playlist " +
   "subscription subscriptions plan plans premium trial code codes coupon voucher vouchers gift balance points rewards orders " +
   "delivery address location map maps time date when where how what why which who without after before while if is are be can " +
   "will do does not no all any every each step steps guide tutorial easy full complete way ways method tips tricks problem " +
   "problems error errors issue issues working work works someone friends friend family contacts contact list lists history " +
   "cache dark mode light theme background wallpaper font text size sound volume camera mic microphone keyboard mouse device " +
   "devices tv first second last other own more box size border color line lines table column row cell sheet document doc " +
   "slide slides button menu icon bar tab window finds shows says opens stops keeps gets comes goes has have had was were " +
   "permanently again now today chatbot bot assistant manager editor maker generator converter downloader player recorder " +
   "builder tracker planner store shop updates feature features option options tool tools").split(" ").forEach(function (w) { COMMON[w] = 1; });
  function sentence(s) {
    return s.split(/\s+/).map(function (w) {
      var lw = w.toLowerCase(), bare = lw.replace(/[^a-z']/g, "");
      // Only "Book" or "book" becomes "book"; "iPhone", "WhatsApp", "PC" and "I" stay as written.
      var plain = w === lw || (w.charAt(0) !== lw.charAt(0) && w.slice(1) === lw.slice(1));
      return COMMON[bare] && plain && w !== "I" ? lw : w;
    }).join(" ");
  }
  // "Kiwi.com" -> "Kiwi": YouTube turns names like that into links to the brand's site (without our code).
  function noTld(s) { return (s || "").replace(/\b([A-Za-z0-9-]+)\.(com|io|net|ai|app|co|org|me|tv|gg|ph|in|uk)\b/gi, "$1"); }
  function trimFiller(a) {
    var rx = /\s+(full guide|step by step( guide)?|complete guide|tutorial|guide|easy|easily|quick|quickly|fast|for beginners|beginners?'?s? guide|in \d+ (seconds|minutes|steps)|20\d\d|new update|update|latest|simple|\(.*\)|\[.*\])$/i, prev;
    a = a.replace(/[\s,.!?:;-]+$/, "");
    do { prev = a; a = a.replace(rx, "").replace(/[\s,.!?:;-]+$/, ""); } while (a !== prev);
    return a;
  }
  // The first line of the pinned comment: one friendly question about the video that invites a reply, nothing beyond
  // the title (rules of the pinned lists, 9 Oct). The editor can change it before copying.
  function question(title, subj) {
    var t = title.replace(SUFFIX, "").trim(), low = t.toLowerCase(), S = noTld(subj), h = 0, i;
    for (i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) >>> 0;
    var pick = function (a) { return a[h % a.length]; };
    if (/crack|keygen|license key|mod apk|modded|hack|cheat|unlocked|trial reset|activator|free premium|premium (for )?free|lifetime free|free lifetime/.test(low))
      return "Stay safe: skip cracked apps and “free premium” offers." + (S ? " Questions about " + S + "? Ask below 👇" : " Ask your questions below 👇");
    var segs = t.split(/\s+[-–—|:]\s+|\s*\|\s*|:\s+/);
    var vs = segs.filter(function (s) { return /\svs\.?\s/i.test(s); })[0];
    if (vs) {
      var p = vs.split(/\s+vs\.?\s+/i).map(function (x) { return noTld(trimFiller(x.trim())); }).filter(Boolean).slice(0, 3);
      if (p.length >= 2) {
        var list = p.length === 2 ? p[0] + " or " + p[1] : p[0] + ", " + p[1] + " or " + p[2];
        return pick([list + ": which would you pick? Tell us below 👇", list + ": which one works better for you? Tell us below 👇"]);
      }
    }
    if (/refund/.test(low)) return "Did your " + (S ? S + " " : "") + "refund come through? Tell us below what happened 👇";
    if (/delete\b.*\baccount|deactivate|close (your |my )?account/.test(low)) {
      var d = t.match(/(?:delete|deactivate|close)\s+(?:your\s+|my\s+)?(.+?)\s+account/i), dn = S || (d ? noTld(d[1]) : "");
      return "Did deleting your " + (dn ? dn + " " : "") + "account work? Let us know below if you got stuck 👇";
    }
    if (/cancel|unsubscribe/.test(low)) {
      var c = t.match(/(?:cancel|unsubscribe from)\s+(?:your\s+|my\s+)?(.+?)\s+(?:subscription|membership|plan|order|trial|account|premium)\b/i);
      var cn = S || (c ? noTld(c[1]) : "");
      return "Did cancelling " + (cn ? cn + " " : "") + "work for you? Let us know below if any step looked different 👇";
    }
    if (/not working|error|\bfix\b|problem|issue|can'?t|won'?t|failed|stuck/.test(low))
      return "Which " + (S ? S + " " : "") + "error are you seeing? Write it below and we'll try to help 👇";
    if (/review|worth it|honest|tested|after \d+ (days|weeks|months)/.test(low))
      return S ? pick(["Do you use " + S + "? Tell us what you think below 👇", "Thinking about " + S + "? Ask your questions below 👇"])
               : "What do you think? Tell us below 👇";
    var how = null;
    segs.forEach(function (s) { var m = !how && s.match(/how\s+to\s+(.+)/i); if (m) how = m[1]; });
    if (how) {
      var a = sentence(trimFiller(noTld(how)));
      if (a.length > 70) a = a.slice(0, 70).replace(/\s+\S*$/, "");
      if (a) return pick(["Managed to " + a + "? Tell us below if you got stuck 👇",
                          "Trying to " + a + "? Ask below if any step looked different for you 👇",
                          "Did you manage to " + a + "? Let us know below if anything was unclear 👇"]);
    }
    if (S) return pick(["Questions about " + S + "? Ask below and we'll try to help 👇", "What are you using " + S + " for? Tell us below 👇"]);
    return "Did this help? Tell us below if any step looked different for you 👇";
  }

  var vt = document.getElementById("vt"), sel = document.getElementById("vtool"), made = document.getElementById("made");
  var pin = document.getElementById("pin"), desc = document.getElementById("desc"), vnote = document.getElementById("vnote");
  var none = document.createElement("option"); none.value = ""; none.textContent = "No link (newsletter line only)"; sel.appendChild(none);
  BOX.items.forEach(function (it) { var o = document.createElement("option"); o.value = it.s; o.textContent = it.n; sel.appendChild(o); });
  var manual = null;
  function makeLines() {
    var title = vt.value.trim();
    made.hidden = !title;
    if (!title) return;
    var tl = " " + title.toLowerCase() + " ", it = null, guide = null, note, j;
    var cancel = CANCEL.test(title), excluded = !cancel && EXCLUDE.test(title);
    if (cancel) {
      for (j = 0; j < gkeys.length && !guide; j++) if (gkeys[j].rx.test(tl)) guide = gkeys[j].g;
      note = guide ? "Cancel video: the cancel guide instead of an affiliate link (our rule)." : "Cancel video: no affiliate link (our rule).";
    } else if (excluded) {
      note = "No affiliate link on videos about refunds, free versions, cracks or alternatives (our rule).";
    } else if (manual !== null) {
      it = bySlug[manual] || null;
      note = it ? "Picked by hand." : "No link: newsletter line only.";
    } else {
      for (j = 0; j < keys.length && !it; j++) if (keys[j].rx.test(tl) && !(keys[j].it.xr && keys[j].it.xr.test(title))) it = keys[j].it;
      note = it ? "Found in the title. Wrong one? Pick another." : "No tool from our list in the title. Pick one if the video is about one.";
    }
    sel.value = it ? it.s : "";
    sel.disabled = cancel || excluded;
    var link = it ? "👉 Try " + it.w + " (affiliate): useandlike.com/" + it.s
             : guide ? "👉 Step-by-step guide: subscriptionchef.app/cancel/" + guide.s : "";
    pin.value = [question(title, it ? it.n : guide ? guide.n : ""), link, BOX.pinNews].filter(Boolean).join("\n");
    desc.value = [link, NEWS].filter(Boolean).join("\n");
    vnote.textContent = note;
    grow(pin); grow(desc);
  }
  function grow(ta) { ta.style.height = "auto"; ta.style.height = ta.scrollHeight + 2 + "px"; }   // whole text visible on phones
  pin.addEventListener("input", function () { grow(pin); });
  desc.addEventListener("input", function () { grow(desc); });
  vt.addEventListener("input", function () { manual = null; makeLines(); });
  sel.addEventListener("change", function () { manual = sel.value; makeLines(); });
"""


def main():
    tools = load_tools()
    os.makedirs(os.path.join(ROOT, "editors"), exist_ok=True)
    print(write_links_page(tools), "links -> team-links/index.html (" + LINKS_PAGE_URL + ")")

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
