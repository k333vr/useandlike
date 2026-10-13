#!/usr/bin/env python3
"""Builds the lists the video editors use for descriptions.

Output (folder editors/, not published on the site):
  tool-links.csv          every tool with its short link
And outside editors/: team-links/index.html, the same links as a hidden page on the site for the manager and
uploaders (LINKS_PAGE_URL: not linked anywhere, noindex, not in the sitemap): a Copy button for each 👉 line, the date
each link was added (from git), what's new and what was removed. It goes live with the next push to main.
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
LINK_ONLY_NAMES = {"biltrx": "BiltRx", "blort": "Blort"}  # short links that aren't tools on the site
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
    links = []
    for slug, target in redirects:
        if (urllib.parse.urlparse(target).hostname or "").endswith(OWN_HOSTS):
            continue
        t = by_slug.get(slug)
        if not t and slug not in LINK_ONLY_NAMES:
            print("WARN: /%s is a short link without a tool or a name: add it to LINK_ONLY_NAMES" % slug)
        name = t["name"] if t else LINK_ONLY_NAMES.get(slug, slug)
        links.append({"slug": slug, "name": name, "cat": t["category"] if t else "Link only (not on the site)",
                      "line": "👉 Try %s (affiliate): useandlike.com/%s" % (LINE_NAME.get(name, name), slug),
                      "added": added.get(slug, today.isoformat())})  # not committed yet: today
    esc = lambda s: html.escape(s, quote=True)

    def row(l):
        note = ""
        if l["name"] in LINE_NAME:
            note = ('<p class="note">Written as “%s” on purpose: YouTube would turn “%s” into a direct link without our '
                    'code.</p>' % (esc(LINE_NAME[l["name"]]), esc(l["name"])))
        new = (today - date.fromisoformat(l["added"])).days < NEW_DAYS
        return ('<div class="row" id="l-{slug}" data-line="{line}" data-q="{q}" data-added="{iso}"><div class="who"><span class="name">{name}'
                '</span>{badge}<span class="date">Added {day}</span></div><code class="line">{line}</code><button '
                'type="button" data-copy aria-label="Copy the line for {name}">Copy</button>{note}</div>\n').format(
            slug=esc(l["slug"]), line=esc(l["line"]), name=esc(l["name"]), note=note, day=nice_day(l["added"]), iso=l["added"],
            q=esc(" ".join([l["name"], l["slug"], l["cat"]]).lower()), badge='<span class="badge">New</span>' if new else "")

    sections = []
    for c in order + sorted({l["cat"] for l in links} - set(order)):
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
    page = (LINKS_TEMPLATE.replace("<!--COUNT-->", str(len(links))).replace("<!--UPDATED-->", nice_day(today.isoformat()))
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
button[data-copy] { font: inherit; font-size: .9rem; font-weight: 600; min-width: 6.8rem; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--brand); background: var(--brand); color: var(--brand-text); cursor: pointer; }
button[data-copy]:hover { filter: brightness(1.12); }
button[data-copy].ok { background: var(--surface); color: var(--ok); border-color: var(--ok); }
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
  function copy(b) {
    var row = b.closest(".row");
    var text = row.dataset.line + (nl.checked ? "\\n" + NEWS : "");
    var fallback = function () {
      if (oldCopy(text)) { flashButton(b, "Copied ✓", true); return; }
      selectLine(row); flashButton(b, "Press Ctrl+C", false);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flashButton(b, "Copied ✓", true); }, fallback);
    } else { fallback(); }
  }
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
    var a = ev.target.closest("a[data-jump]");
    if (a) { ev.preventDefault(); jump(a.dataset.jump); }
  });
})();
</script>
</body>
</html>
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
