#!/usr/bin/env python3
"""Builds the lists the video editors use for descriptions.

Output (folder editors/, not published on the site):
  tool-links.csv          every tool with its short link
And outside editors/: team-links/index.html, the same links as a hidden page on the site for the manager and
uploaders (LINKS_PAGE_URL: not linked anywhere, noindex, not in the sitemap): a Copy button for each 👉 line, the date
each link was added (from git), what's new and what was removed, and a box that turns a new video's title into the
pinned comment (a question + the 👉 line + the newsletter line) and a short description (our lines, one sentence that
extends the title without promises, the closing line; Kevin: "more short not overpromising"), with the same title rules as
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
NEWSLETTER_LINK = re.compile(r"^n\d+-")  # /n1-... = newsletter issue links (the _redirects block newsletter-links): not for the team
# Names and groups of the short links that aren't tools on the site (most written by useandlike-ops/analysis/yazing-add.py).
SHORT_LINKS = os.path.join(ROOT, "data", "short-links.json")
TITLE_FIXES = os.path.join(ROOT, "data", "title-fixes.json")
# Game videos to move to the Gaming category (and pick the game), from useandlike-ops/analysis/game-category.py.
GAME_FIXES = os.path.join(ROOT, "data", "game-category.json")
# Video topics that pay (Kevin, 16 Oct: "focus on high RPM topics"; for Kevin, who picks the topics in another app; the team
# uses this page only for the affiliate apps' names), from
# useandlike-ops/analysis/topic-ideas-page.py (the Studio exports' money per topic; names only, no money figures).
TOPIC_IDEAS = os.path.join(ROOT, "data", "topic-ideas.json")
# Everyday English words (lowercase in a sentence), for the new-video box: see the file's header.
COMMON_WORDS = os.path.join(ROOT, "data", "common-words.txt")
# What each link is for (Kevin, 29 Oct: "the editor then has field where he types in budget and/or budgeting and get the
# list of all affiliate offers that fit"): the page's search finds links by topic, and the new-video box suggests the
# offers whose topics a title names when it names none of our tools. See the file's _about.
OFFER_TOPICS = os.path.join(ROOT, "data", "offer-topics.json")
# Last line of a pinned comment (the description uses NEWSLETTER_LINE); same as useandlike-ops/analysis/pinned-comment-lines.py.
PINNED_NEWS = "📩 Free Subscription Tracker + new app tips by email: useandlike.com/join"
# Link-only names that are ordinary words: the page's "new video" box doesn't pick them from a title by itself.
NO_AUTO = {"box", "changed", "rover", "knack", "reverb", "lot", "empower", "parallels", "pigment", "condor", "optimum",
           "acorns", "carla"}
# First words of link names that say too little: "Keeper Security" and "Xfinity Mobile" are found by their full names
# only ("Zoo Keeper", "Xfinity router" videos are about something else).
NO_AUTO_FIRST = {"keeper", "xfinity"}
# Like bv.NOT_ABOUT for the site's tools: other products with a link-only brand's name.
LINK_NOT_ABOUT = {"Alibaba": re.compile(r"\bqwen|alibaba cloud|aliyun", re.I),
                  "Recruit CRM": re.compile(r"\bassignment|\binterview|\bjobs?\b|\bcareers?\b|\bcsa\b", re.I)}  # working there
# Links that only go on some videos about their tool (Kevin, 14 Oct, Skool: "only add it if it really makes sense to make a
# community from the video"): the title has to match. Settings videos are for people who already use it.
LINK_ONLY_IF = {
    "Skool": re.compile(r"^(?!.*\b(profile|password|e-?mail address|time ?zone|invoice|billing|bank|payouts?|notifications?|"
                        r"settings?|log ?in|login|username|language|delete|deactivate|leave|unsubscribe|cancel)\b)"
                        r".*\b(creat\w*|start\w*|build\w*|launch\w*|set ?up|setting up|sign(ing)? ?up|make money|monetiz\w*|"
                        r"paid (community|communities|group|membership)|pric\w*|cost\w*|worth it|reviews?|vs\.?|versus|"
                        r"compar\w*|tutorial|beginners?|what is|explained)\b", re.I),
    # Whop's partner link pays when a business starts selling on Whop (Kevin, 14 Oct): not for buyers, members or clippers.
    "Whop": re.compile(r"^(?!.*\b(clip\w*|content rewards?|affiliates?|join\w*|buy\w*|purchas\w*|cancel\w*|refund\w*|delete|"
                       r"leave|log ?in|login|password|payouts?)\b)"
                       r".*\b(sell\w*|stores?|shop|digital products?|courses?|communit\w*|memberships?|start\w*|launch\w*|"
                       r"set ?up|setting up|creat\w*|build\w*|checkout|accept\w* payments?|pric\w*|fees?|vs\.?|versus|"
                       r"compar\w*|reviews?|tutorial|beginners?|what is|explained)\b", re.I),
}
LINK_ONLY_NOTE = {"Skool": "Only on videos for people who would start their own community: creating one, getting started, "
                           "Skool vs …, reviews, pricing, tutorials. Not on settings videos (profile, password, payouts …).",
                  "Whop": "Only on videos for people who would start selling on Whop: selling products, communities or "
                          "courses, setting up a store, Whop vs …, reviews. Not on clipping, buying or joining videos."}
# Links a network allows on one channel only: "only" in data/short-links.json (FlexOffers, 15 Oct: it approved How To
# Rocket and turned down useandlike.com and Guide Glimpse). The page marks them, and the new-video box offers them only
# once the uploader has picked that channel. scripts/check.js keeps FlexOffers links off the site's Visit buttons.
CHANNEL_NAMES = {"htr": "How To Rocket", "gg": "Guide Glimpse", "lp": "Logic Protocol"}
NEW_DAYS = 7  # "New" badge
NEWS_DAYS = 30  # how far back "What's new" and "Removed" look
FOLD = 40  # a day in "What's new" with more than FOLD + 10 new links shows the rest behind "N more"
CANCEL = re.compile(r"\bcancel|unsubscribe|end (your |my )?(membership|subscription)|stop (your |my )?subscription", re.I)
SEGMENTS = re.compile(r"\s+[-–—|:]\s+|\s*\|\s*|:\s+")  # title parts ("Hostinger vs IONOS: 5 Truths" -> 2 parts)
VS = re.compile(r"\s+vs\.?\s+", re.I)
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


def link_keys(l):
    """How the page's box and lines_for find a link-only short link in a title: its name (not the ones in NO_AUTO), and
    a name's first word when it is the slug ("CyberGhost VPN" also as "cyberghost")."""
    n = l["name"].lower()
    k = [] if n in NO_AUTO else [n]
    first = (re.findall(r"[a-z0-9]+", n) or [""])[0]
    if k and " " in n and first == l["slug"] and len(first) >= 5 and first not in NO_AUTO_FIRST:
        k.append(first)
    return k


def make_matcher(tools, links=None):
    """Returns lines_for(title, channel=None) -> (kind, [lines to put at the top of the description]). With links
    (read_links), the link-only short links count too, found by their names as in the page's box (29 Oct: uploads about
    DistroKid, Trip.com ... got no 👉 line); a link for one channel only ("only" in short-links.json) needs that channel."""
    href = {t["name"]: "useandlike.com/" + t["slug"] for t in tools}
    written = {t["name"]: LINE_NAME.get(t["name"], t["name"]) for t in tools}
    only = {}
    guides = [(k, slug) for slug, _, keys in cancel_guides() for k in keys]
    guides.sort(key=lambda k: -len(k[0]))
    gpat = [(re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])"), s) for k, s in guides]
    keys = [(k, t["name"]) for t in tools for k in bv.ALIASES.get(t["name"], [t["name"].lower()])]
    for l in links or []:
        if not l["tool"] and l["name"] not in href:
            href[l["name"]], written[l["name"]], only[l["name"]] = l["href"], l["written"], l["only"]
            keys += [(k, l["name"]) for k in link_keys(l)]
    keys.sort(key=lambda k: -len(k[0]))
    tpat = [(re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])"), n) for k, n in keys]

    not_about = {**bv.NOT_ABOUT, **LINK_NOT_ABOUT}

    def tool_in(text, title, channel):
        # Same "other product with the same name" rule as the site (bv.NOT_ABOUT): no Wise link on Wise Care videos.
        tl = " " + text.lower() + " "
        return next((n for rx, n in tpat if rx.search(tl) and not (n in not_about and not_about[n].search(title))
                     and not (n in LINK_ONLY_IF and not LINK_ONLY_IF[n].search(title))
                     and (not only.get(n) or only[n] == channel)), None)

    def lines_for(title, channel=None):
        tl = " " + title.lower() + " "
        if CANCEL.search(title):
            g = next((s for rx, s in gpat if rx.search(tl)), None)
            if g:
                return "cancel guide", ["👉 Step-by-step guide: subscriptionchef.app/cancel/" + g, NEWSLETTER_LINE]
        elif not bv.EXCLUDE.search(title):
            # "A vs B (vs C)": a 👉 line for each compared tool we have a link for, in the title's order (13 Oct).
            found = []
            vs = next((s for s in SEGMENTS.split(title) if VS.search(s)), None)
            m = vs and re.search(r"\(([^()]*\svs\.?\s[^()]*)\)", vs, re.I)   # "… (Fiverr Pro vs Fiverr)"
            vs = m.group(1) if m else vs
            for part in VS.split(vs)[:3] if vs else []:
                tool = tool_in(part, title, channel)
                if tool and tool not in found:
                    found.append(tool)
            if len(found) < 2:
                found = [t for t in [tool_in(title, title, channel)] if t]
            if found:
                return "tool", ["👉 Try %s (affiliate): %s" % (written[t], href[t]) for t in found] + [NEWSLETTER_LINE]
        return "newsletter only", [NEWSLETTER_LINE]
    return lines_for


def norm(s):
    """Lowercase words and digits only, as the page's box compares them ("50/30/20 Budget" -> "50 30 20 budget")."""
    return re.sub(r"[^a-z0-9']+", " ", s.lower().replace("’", "'").replace("‘", "'")).strip()


def load_topics(slugs):
    """data/offer-topics.json as (sets, offers): set name -> [phrases], slug -> ["@set" or phrase], phrases normalized.
    Warns about slugs that aren't short links and sets that don't exist."""
    if not os.path.exists(OFFER_TOPICS):
        return {}, {}
    d = json.load(open(OFFER_TOPICS, encoding="utf-8"))
    sets = {k: list(dict.fromkeys(norm(p) for p in v)) for k, v in d.get("sets", {}).items()}
    offers = {}
    for slug, refs in d.get("offers", {}).items():
        if slug not in slugs:
            print("WARN: data/offer-topics.json names /%s, which isn't a short link" % slug)
        for r in refs:
            if r.startswith("@") and r[1:] not in sets:
                print("WARN: data/offer-topics.json: /%s uses the unknown set %s" % (slug, r))
        offers[slug] = [r if r.startswith("@") else norm(r) for r in refs if not r.startswith("@") or r[1:] in sets]
    return sets, offers


def topic_phrases(refs, sets):
    return list(dict.fromkeys(p for r in refs for p in (sets[r[1:]] if r.startswith("@") else [r])))


def topic_matcher(links, sets, offers):
    """fits(title, channel=None) -> [(link, phrase)]: the links whose topics the title names (a plural "s"/"es" on the
    phrase's last word counts too), most specific phrase first, then links with a deal on our deals page, tools on the
    site, what a link is worth. The same order as the page's box. Links for one channel only need that channel;
    LINK_ONLY_IF rules apply."""
    table = [(l, topic_phrases(offers[l["slug"]], sets)) for l in links if l["slug"] in offers]

    def fits(title, channel=None):
        t, out = " " + norm(title) + " ", []
        for l, phrases in table:
            if (l["only"] and l["only"] != channel) or (l["name"] in LINK_ONLY_IF and not LINK_ONLY_IF[l["name"]].search(title)):
                continue
            hit = [p for p in phrases if any(" %s%s " % (p, e) in t for e in ("", "s", "es"))]
            if hit:
                out.append((l, max(hit, key=lambda p: len(p.split()))))
        out.sort(key=lambda x: (-len(x[1].split()), not x[0]["deal"], not x[0]["tool"], -x[0]["worth"], x[0]["name"].lower()))
        return out
    return fits


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


def topics_section(esc):
    """The "Video topics that pay" box (empty without data/topic-ideas.json)."""
    if not os.path.exists(TOPIC_IDEAS):
        return ""
    d = json.load(open(TOPIC_IDEAS, encoding="utf-8"))
    li = lambda xs: "".join("<li>%s</li>" % esc(x) for x in xs)
    chips = lambda xs: "".join('<span class="tp-chip%s">%s</span>' % (" earn" if earn else "", esc(n)) for n, earn in xs)
    more = chips([(a["name"], a["earn"]) for a in d["apps_more"]])
    skip = chips([(n, False) for n in d["apps_skip"]])
    searches = chips([(s, False) for s in d["searches"]])
    flex = "".join('<div class="tp-tool"><b>%s</b> <span class="tp-pays">%s</span><ul>%s</ul></div>' % (
        esc(f["name"]), esc(f["pays"]), li(f["ideas"])) for f in d["flex"])
    groups, n_open = [], 0
    for g in d["open"]:
        tools = []
        for t in g["tools"]:
            n_open += len(t["searches"])
            tools.append('<div class="tp-tool"><b>%s</b> <code>useandlike.com/%s</code><ul>%s</ul></div>' % (
                esc(t["tool"]), esc(t["slug"]), li(t["searches"])))
        groups.append('<div class="tp-group"><h4>%s</h4><div class="tp-tools">%s</div></div>' % (esc(g["group"]), "".join(tools)))
    return """  <section class="maker" id="topics" aria-labelledby="topics-h">
    <h2 id="topics-h">Video topics that pay</h2>
    <p class="hint">From our own channel numbers (updated %s). Topics on the left earn up to 10 times more per view than
      the ones on the right. Put the words people search first in every title; hooks only on comparisons and reviews.</p>
    <div class="tp-cols">
      <div><h3>Make more about</h3><ul class="tp-list">%s</ul><p class="tp-apps">%s</p></div>
      <div><h3>Skip</h3><ul class="tp-list">%s</ul><p class="tp-apps">%s</p></div>
    </div>
    <p class="hint"><span class="tp-chip earn">Green</span> = we have an affiliate link for it.</p>
    <details class="tp-more"><summary>Comparisons people search that already bring viewers to us (%d)</summary>
      <p class="tp-apps">%s</p></details>
    <details class="tp-more"><summary>How To Rocket only: FlexOffers apps (links come once each app approves us) (%d)</summary>
      <div class="tp-tools">%s</div></details>
    <details class="tp-more"><summary>Ready topics: searches with no video from us yet, for apps we earn from (%d)</summary>
      <input id="tq" type="search" placeholder="Find, e.g. Shopify, vs, pricing" aria-label="Find a ready topic" autocomplete="off">
      %s</details>
  </section>
""" % (esc(nice_day(d["made"])), li(d["pay_well"]), more, li(d["pay_badly"]), skip, len(d["searches"]), searches,
       len(d["flex"]), flex, n_open, "".join(groups))


def read_links(tools):
    """Every affiliate short link in _redirects (our own links and newsletter links left out) with its name, group, 👉 line,
    channel rule, and for ordering suggestions: whether it's a tool on the site and what it's worth (short-links.json)."""
    redirects = re.findall(r"^/([\w-]+)\s+(\S+)", open(os.path.join(ROOT, "_redirects"), encoding="utf-8").read(), re.M)
    by_slug = {t["slug"]: t for t in tools}
    extra = json.load(open(SHORT_LINKS, encoding="utf-8")) if os.path.exists(SHORT_LINKS) else {}
    deals = os.path.join(ROOT, "data", "deals.json")   # a deal on our deals page right now: suggested first
    deals = {d["slug"] for d in json.load(open(deals, encoding="utf-8"))["deals"]} if os.path.exists(deals) else set()
    links = []
    for slug, target in redirects:
        if (urllib.parse.urlparse(target).hostname or "").endswith(OWN_HOSTS) or NEWSLETTER_LINK.match(slug):
            continue
        t, x = by_slug.get(slug), extra.get(slug, {})
        if not t and not x:
            print("WARN: /%s is a short link without a tool or a name: add it to data/short-links.json" % slug)
        name = t["name"] if t else x.get("name", slug)
        written = LINE_NAME.get(name, name) if t else x.get("line_name", name)
        # "direct": the brand's own link goes in the 👉 line, because its rules forbid masked links (Synthesia, 30 Oct:
        # "Don't Mask or Hide Affiliate Links"); a site tool always uses its short link (the Visit button needs it).
        href = target if x.get("direct") and not t else "useandlike.com/" + slug
        links.append({"slug": slug, "name": name, "cat": t["category"] if t else x.get("group", "Other"), "written": written,
                      "line": "👉 Try %s (affiliate): %s" % (written, href), "href": href,
                      "only": x.get("only", ""), "source": x.get("source", ""),
                      "tool": bool(t), "worth": float(x.get("worth") or 0), "deal": slug in deals})
    return links


def write_links_page(tools):
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    order = bv.read_js_array(src, "CATEGORIES")
    added, removed = link_history()
    today = date.today()
    by_slug = {t["slug"]: t for t in tools}
    # For the manager (the page's "To fix in YouTube Studio" popup), written by useandlike-ops/analysis/title-fixes.py
    # and game-category.py
    title_fixes = json.load(open(TITLE_FIXES, encoding="utf-8")) if os.path.exists(TITLE_FIXES) else []
    game_fixes = json.load(open(GAME_FIXES, encoding="utf-8")) if os.path.exists(GAME_FIXES) else []
    links = read_links(tools)
    for l in links:
        l["added"] = added.get(l["slug"], today.isoformat())  # not committed yet: today
    sets, offers = load_topics({l["slug"] for l in links})
    esc = lambda s: html.escape(s, quote=True)

    def row(l):
        note = ""
        if l["written"] != l["name"]:
            note = ('<p class="note">Written as “%s” on purpose: YouTube would turn “%s” into a direct link without our '
                    'code.</p>' % (esc(l["written"]), esc(l["name"])))
        if l["name"] in LINK_ONLY_NOTE:
            note += '<p class="note">%s</p>' % esc(LINK_ONLY_NOTE[l["name"]])
        if l["href"] != "useandlike.com/" + l["slug"]:
            note += ('<p class="note">%s doesn’t allow short links: always paste this full link, never '
                     'useandlike.com/%s.</p>' % (esc(l["name"]), esc(l["slug"])))
        only = CHANNEL_NAMES.get(l["only"], "")
        if only:
            note += ('<p class="note">Only on %s videos: %s approved only that channel. Never on the other channels or '
                     'the website.</p>' % (esc(only), esc(l["source"] or "the network")))
        new = (today - date.fromisoformat(l["added"])).days < NEW_DAYS
        topics = topic_phrases(offers.get(l["slug"], []), sets)   # the search finds a link by its topics too ("budget")
        return ('<div class="row" id="l-{slug}" data-line="{line}" data-q="{q}" data-added="{iso}"><div class="who"><span class="name">{name}'
                '</span>{badge}{only}<span class="date">Added {day}</span></div><code class="line">{line}</code><button '
                'type="button" data-copy aria-label="Copy the line for {name}">Copy</button>{note}</div>\n').format(
            slug=esc(l["slug"]), line=esc(l["line"]), name=esc(l["name"]), note=note, day=nice_day(l["added"]), iso=l["added"],
            q=esc(" | ".join(filter(None, [l["name"], l["slug"], l["cat"], only] + topics)).lower()),
            badge='<span class="badge">New</span>' if new else "", only='<span class="only">%s only</span>' % esc(only) if only else "")

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
            k, x = link_keys(l), LINK_NOT_ABOUT.get(l["name"])
        o = LINK_ONLY_IF.get(l["name"])
        # tp: its topics ("@set" or a phrase); dl: a deal on our deals page, st: a tool on the site, v: what it's worth
        # (these three order the topic suggestions)
        # d: what it is, for the video-plan prompt (a site tool's description, else its group and first topics)
        about = ", ".join(topic_phrases(offers.get(l["slug"], []), sets)[:3])
        items.append({"s": l["slug"], "n": l["name"], "w": l["written"], "k": k, "x": x.pattern if x else "",
                      "d": by_slug[l["slug"]]["description"] if l["slug"] in by_slug else l["cat"] + (" (" + about + ")" if about else ""),
                      "o": o.pattern if o else "", "on": LINK_ONLY_NOTE.get(l["name"], ""), **({"c": l["only"]} if l["only"] else {}),
                      **({"u": l["href"]} if l["href"] != "useandlike.com/" + l["slug"] else {}),   # its own link, no short link
                      **({"tp": offers[l["slug"]], "dl": int(l["deal"]), "st": int(l["tool"]), "v": l["worth"]}
                         if offers.get(l["slug"]) else {})})
    box = {"items": items, "sets": sets, "guides": [{"s": s, "n": n, "k": k} for s, n, k in cancel_guides()],
           "exclude": bv.EXCLUDE.pattern, "cancel": CANCEL.pattern, "suffix": bv.SUFFIX.pattern, "pinNews": PINNED_NEWS,
           "common": " ".join(l.strip() for l in open(COMMON_WORDS, encoding="utf-8") if l.strip() and not l.startswith("#"))}
    page = (LINKS_TEMPLATE.replace("/*BOX_JS*/", BOX_JS).replace("/*BOX*/", json.dumps(box, ensure_ascii=False).replace("</", "<\\/"))
            .replace("<!--COUNT-->", str(len(links))).replace("<!--UPDATED-->", nice_day(today.isoformat()))
            .replace("<!--NEWSLETTER-->", esc(NEWSLETTER_LINE)).replace("/*NEWSLETTER*/", json.dumps(NEWSLETTER_LINE))
            .replace("<!--NEW_DAYS-->", str(NEW_DAYS)).replace("/*NEW_DAYS*/", str(NEW_DAYS))
            .replace("<!--NEWS-->", "".join(news)).replace("<!--LIST-->", "".join(sections))
            .replace("/*TITLE_FIXES*/", json.dumps(title_fixes, ensure_ascii=False).replace("</", "<\\/"))
            .replace("/*GAME_FIXES*/", json.dumps(game_fixes, ensure_ascii=False).replace("</", "<\\/"))
            .replace("<!--TOPICS-->", topics_section(esc)))
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
  --ok: #2d6a4f; --ok-bg: #e3f1e7; --new-bg: #f5ead2; --new-fg: #6f5216; --flash: #f8edcf;
  --serif: Georgia, "Times New Roman", serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #121417; --surface: #191c21; --text: #ebe9e4; --muted: #a7abb3; --line: #2e333b;
    --brand: #a9c2e6; --brand-text: #121417; --brass: #d4b06a; --link: #a6c3f5; --soft: #1d2127;
    --ok: #8fd1ae; --ok-bg: #16271e; --new-bg: #2e2719; --new-fg: #e2c38a; --flash: #2b2618; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #121417; --surface: #191c21; --text: #ebe9e4; --muted: #a7abb3; --line: #2e333b;
  --brand: #a9c2e6; --brand-text: #121417; --brass: #d4b06a; --link: #a6c3f5; --soft: #1d2127;
  --ok: #8fd1ae; --ok-bg: #16271e; --new-bg: #2e2719; --new-fg: #e2c38a; --flash: #2b2618; color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 16px/1.5 var(--sans); }
.wrap { max-width: 980px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 48px; }
.eyebrow { margin: 0; font-size: .78rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--brass); }
h1 { font-family: var(--serif); font-weight: 400; font-size: clamp(1.9rem, 5vw, 2.5rem); line-height: 1.15; margin: .3rem 0 .6rem; color: var(--brand); text-wrap: balance; }
.lede { margin: 0; max-width: 64ch; }
.rule { margin: .7rem 0 0; max-width: 70ch; padding: 10px 14px; border-radius: 8px; background: var(--new-bg); color: var(--new-fg); font-size: .95rem;
        display: grid; gap: 6px; }
.rule p { margin: 0; }
.rule-lines { margin: 0; padding-left: 1.4em; display: grid; gap: 2px; }
.rule-lines code { overflow-wrap: anywhere; }
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
.only { font-size: .7rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--new-fg); border: 1px solid var(--brass); border-radius: 4px; padding: 0 5px; }
.date { flex-basis: 100%; font-size: .8rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.line { font-size: .88rem; min-width: 0; overflow-wrap: anywhere; }
button[data-copy], button[data-copyout], button[data-tfcopy], button[data-copytext] { font: inherit; font-size: .9rem; font-weight: 600; min-width: 6.8rem; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--brand); background: var(--brand); color: var(--brand-text); cursor: pointer; }
button[data-copy]:hover, button[data-copyout]:hover, button[data-tfcopy]:hover, button[data-copytext]:hover { filter: brightness(1.12); }
button[data-copy].ok, button[data-copyout].ok, button[data-tfcopy].ok, button[data-copytext].ok { background: var(--surface); color: var(--ok); border-color: var(--ok); }
.outro-lines { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.outro-lines li { display: flex; gap: 10px 14px; align-items: center; justify-content: space-between; flex-wrap: wrap; padding: 8px 0; border-bottom: 1px solid var(--line); }
.outro-lines span { flex: 1 1 18rem; min-width: 0; }
.outro-cards { margin: 0; font-size: .92rem; }
.outro-cards a { color: var(--link); }
.maker { margin-top: 20px; padding: 16px 18px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); display: grid; gap: 10px; }
.maker h2 { font-family: var(--serif); font-weight: 400; font-size: 1.35rem; margin: 0; }
.maker .hint { margin: 0; max-width: 70ch; font-size: .9rem; color: var(--muted); }
.field, .pickrow label, .outhead span { font-size: .9rem; font-weight: 600; }
#vt, #vtool, #vch, .out textarea { font: inherit; width: 100%; min-width: 0; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--text); }
#made { display: grid; gap: 12px; }
.pickrow { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }
.pickrow[hidden] { display: none; }
#vtool, #vch { width: auto; max-width: 100%; flex: 0 1 22rem; }
.vnote { font-size: .85rem; color: var(--muted); }
.out { display: grid; gap: 6px; }
.outhead { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.out textarea { font-family: var(--mono); font-size: .86rem; line-height: 1.45; resize: vertical; }
.vstatus { margin: 0; padding: 8px 12px; border-radius: 8px; font-weight: 600; background: var(--soft); }
.vstatus.yes { background: var(--ok-bg); color: var(--ok); }
.vstatus.warn { background: var(--new-bg); color: var(--new-fg); }
.vtopics { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: .9rem; }
.vtopics[hidden] { display: none; }
.vtopics b { font-weight: 600; margin-right: 2px; }
.vtopics button { font: inherit; font-size: .88rem; padding: 3px 12px; border-radius: 999px; border: 1px solid var(--line);
  background: var(--bg); color: var(--link); cursor: pointer; }
.vtopics button:hover { border-color: var(--link); }
.vtopics button[aria-pressed="true"] { background: var(--ok-bg); color: var(--ok); border-color: var(--ok); font-weight: 600; }
.vtopics .all { border-style: dashed; color: var(--muted); }
.opt.small { font-size: .85rem; }
:focus-visible { outline: 3px solid var(--brass); outline-offset: 2px; }
.note { grid-column: 2 / -1; margin: 0; font-size: .8rem; color: var(--muted); }
.row.flash { background: var(--flash); }
.none { margin-top: 24px; padding: 14px 16px; border: 1px dashed var(--line); border-radius: 10px; color: var(--muted); }
footer { margin-top: 36px; max-width: 70ch; font-size: .85rem; color: var(--muted); }
/* Titles to fix (Kevin, 15 Oct): a popup for the manager, opened once a day while some are left */
.tf-open { margin-top: 12px; font: inherit; font-size: .9rem; font-weight: 600; padding: 8px 14px; border-radius: 8px;
  border: 1px solid var(--brass); background: var(--new-bg); color: var(--new-fg); cursor: pointer; }
dialog.tf { width: min(760px, calc(100vw - 24px)); max-height: calc(100vh - 32px); padding: 0; border: 1px solid var(--line);
  border-radius: 12px; background: var(--surface); color: var(--text); }
dialog.tf::backdrop { background: rgba(0, 0, 0, .45); }
.tf-head { position: sticky; top: 0; z-index: 1; background: var(--surface); padding: 16px 52px 12px 18px; border-bottom: 1px solid var(--line); display: grid; gap: 6px; }
.tf-head h2 { font-family: var(--serif); font-weight: 400; font-size: 1.35rem; margin: 0; }
.tf-head p { margin: 0; font-size: .88rem; color: var(--muted); max-width: 70ch; }
.tf-close { position: absolute; top: 10px; right: 10px; font: inherit; font-size: 1.2rem; line-height: 1; padding: 8px 10px; border: 0;
  border-radius: 8px; background: transparent; color: var(--muted); cursor: pointer; }
.tf-list { list-style: none; margin: 0; padding: 0 18px 18px; }
.tf-item { padding: 12px 0; border-bottom: 1px solid var(--line); display: grid; gap: 6px; }
.tf-item.done { opacity: .5; }
.tf-meta { font-size: .76rem; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: var(--muted); }
.tf-old { margin: 0; font-size: .88rem; color: var(--muted); text-decoration: line-through; overflow-wrap: anywhere; }
.tf-new { margin: 0; font-weight: 600; overflow-wrap: anywhere; }
.tf-do { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; font-size: .9rem; }
.tf-do a { color: var(--link); }
.tf-do label { display: flex; gap: 6px; align-items: center; cursor: pointer; }
.tf-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.tf-tabs button { font: inherit; font-size: .88rem; font-weight: 600; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--line);
  background: transparent; color: var(--muted); cursor: pointer; }
.tf-tabs button[aria-selected="true"] { background: var(--new-bg); color: var(--new-fg); border-color: var(--brass); }
.tf-how { margin: 14px 18px 0; font-size: .88rem; color: var(--muted); max-width: 70ch; }
.tf-title { margin: 0; font-weight: 600; overflow-wrap: anywhere; }
.tf-game { margin: 0; font-size: .92rem; overflow-wrap: anywhere; }
.tf-game span { color: var(--muted); }
/* Video topics that pay (16 Oct) */
.tp-cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px 24px; }
.tp-cols > div { min-width: 0; }
.tp-cols h3, .tp-group h4 { margin: 0 0 4px; font-size: 1rem; font-weight: 600; }
.tp-list { margin: 0 0 8px; padding-left: 18px; display: grid; gap: 2px; font-size: .95rem; }
.tp-apps { margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
.tp-chip { font-size: .85rem; padding: 2px 10px; border-radius: 999px; border: 1px solid var(--line); background: var(--bg); }
.tp-chip.earn { background: var(--ok-bg); color: var(--ok); border-color: var(--ok); }
.tp-more { border-top: 1px solid var(--line); padding-top: 10px; }
.tp-more summary { cursor: pointer; color: var(--link); font-weight: 600; font-size: .95rem; }
.tp-more[open] summary { margin-bottom: 10px; }
#tq { font: inherit; width: 100%; padding: 8px 12px; margin-bottom: 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--text); }
.tp-group { margin-bottom: 14px; }
.tp-tools { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; }
.tp-tool { min-width: 0; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); font-size: .9rem; }
.tp-tool code { font-size: .78rem; color: var(--muted); }
.tp-tool ul { margin: 6px 0 0; padding-left: 18px; display: grid; gap: 2px; overflow-wrap: anywhere; }
.tp-pays { color: var(--muted); font-size: .82rem; }
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
    <div class="rule" role="note">
      <p><b>📌 For Klent and every uploader:</b> the 👉 line is always <b>line 1</b> of the description and the 📩 line
        <b>line 2</b>. YouTube shows only the first lines before “…more”, so a link further down earns almost nothing.</p>
      <ol class="rule-lines"><li><code>👉 Try Fiverr (affiliate): useandlike.com/fiverr</code> (the video’s own 👉 line from this page)</li>
        <li><code><!--NEWSLETTER--></code></li><li>an empty line, then your description</li></ol>
      <p>Don’t move it down or rewrite it as “🔗 Get …”, also when ChatGPT writes the description (the “Longer description”
        prompt below keeps our lines on top). On 29 Oct Kevin had the link moved back to line 1 on the uploads from 20-29 Oct
        where it sat further down.</p>
    </div>
    <p class="meta"><b><!--COUNT--></b> links · updated <!--UPDATED--></p>
    <p class="nl-line">Newsletter line, added when you tick the box below: <code><!--NEWSLETTER--></code></p>
    <button type="button" id="tf-open" class="tf-open" hidden>✏️ To fix in YouTube Studio: <span id="tf-left"></span></button>
  </header>

  <dialog id="tf" class="tf" aria-labelledby="tf-h">
    <div class="tf-head">
      <h2 id="tf-h">To fix in YouTube Studio</h2>
      <p>For the manager: open each video in YouTube Studio, make the change, save, then tick Done. Busiest videos first.
        Ticks stay on this device; fixed videos drop off the list at the next check.</p>
      <div class="tf-tabs" role="tablist">
        <button type="button" role="tab" id="tf-t-titles" aria-controls="tf-p-titles" aria-selected="true">Titles <span></span></button>
        <button type="button" role="tab" id="tf-t-games" aria-controls="tf-p-games" aria-selected="false">Game videos <span></span></button>
      </div>
      <button type="button" class="tf-close" aria-label="Close">✕</button>
    </div>
    <div id="tf-p-titles" role="tabpanel" aria-labelledby="tf-t-titles">
      <p class="tf-how">These titles lost a “?”, a colon, a dot or an apostrophe, or have double spaces, ALL CAPS or an old
        year. Copy the new title and paste it as the title. Only the title changes.</p>
      <ol id="tf-list" class="tf-list"></ol>
    </div>
    <div id="tf-p-games" role="tabpanel" aria-labelledby="tf-t-games" hidden>
      <p class="tf-how">Game videos filed as “Howto &amp; Style”. In Studio: Details → Show more → Category: <b>Gaming</b>.
        A “Game title” field appears: type the game shown below and pick it from the list. That links the video to the
        game’s page on YouTube. Nothing else changes.</p>
      <ol id="tf-glist" class="tf-list"></ol>
    </div>
  </dialog>

  <section class="maker" aria-labelledby="maker-h">
    <h2 id="maker-h">New video? Paste its title</h2>
    <p class="hint">You see at once whether we have an affiliate link for it, and you get the pinned comment (a question
      that invites replies, the 👉 line, the newsletter line) and a short description: our links first, one sentence that
      extends the title, the closing line. Check the link and the text, change them if needed, then copy. No app name in
      the title? The box shows our offers that fit its topic (a budget video: budgeting apps): pick one only if it really
      fits the video. Writing a longer description with an AI? Copy the prompt at the bottom: it keeps our lines on top.</p>
    <div class="pickrow" id="vchrow" hidden><label for="vch">Channel</label><select id="vch"><option value="">Pick the channel</option>
      <option value="htr">How To Rocket</option><option value="gg">Guide Glimpse</option><option value="lp">Logic Protocol</option></select>
      <span class="vnote">Some links are for one channel only.</span></div>
    <label class="field" for="vt">Video title</label>
    <input id="vt" type="text" autocomplete="off" placeholder="e.g. How to Book a Flight Ticket on Kiwi.com">
    <div id="made" hidden>
      <p id="vstatus" class="vstatus" role="status"></p>
      <div id="vtopics" class="vtopics" hidden></div>
      <div class="pickrow"><label for="vtool">Link</label><select id="vtool"></select><span id="vnote" class="vnote"></span></div>
      <div class="out"><div class="outhead"><span>Pinned comment</span><button type="button" data-copyout="pin">Copy</button></div>
        <textarea id="pin" rows="4" spellcheck="false" aria-label="Pinned comment"></textarea></div>
      <div class="out"><div class="outhead"><span>Description</span><button type="button" data-copyout="desc">Copy</button></div>
        <textarea id="desc" rows="6" spellcheck="false" aria-label="Description"></textarea>
        <label class="opt small" for="onlytop"><input id="onlytop" type="checkbox"><span>Only our top lines <em>(to put above an old video's description)</em></span></label></div>
      <div class="out"><div class="outhead"><span>Longer description: prompt for ChatGPT or another AI</span><button type="button" data-copyout="aiprompt">Copy</button></div>
        <textarea id="aiprompt" rows="6" spellcheck="false" aria-label="Prompt for a longer description"></textarea>
        <p class="vnote">Paste it into the AI, then paste its answer as the description. Our lines stay at the very top, where
          viewers see them without tapping “more”. Don’t move the link further down or add “🔗 Get …” lines.</p></div>
      <div class="out"><div class="outhead"><span>Video plan for the editor: prompt for ChatGPT or another AI</span><button type="button" data-copyout="planprompt">Copy</button></div>
        <textarea id="planprompt" rows="6" spellcheck="false" aria-label="Prompt for a video plan"></textarea>
        <p class="vnote">Gives the editor a scene-by-scene plan: the viewer’s problem solved first, then at most one of our
          offers where it really helps (or none). If the plan uses one of our offers, pick it under Link above so the 👉 line
          matches. The plan is a starting point: change anything that doesn’t fit the video.</p></div>
    </div>
  </section>

  <section class="maker" aria-labelledby="outro-h">
    <h2 id="outro-h">Outro for every new video</h2>
    <p class="hint">Say one of these lines at the very end of every new video. An end-card picture is optional: show it for the
      last 3–5 seconds, before YouTube's end screen.</p>
    <ul class="outro-lines">
      <li><span>Want to see what all your subscriptions cost? Get our free Subscription Tracker: the link is in the description.</span><button type="button" data-copytext="Want to see what all your subscriptions cost? Get our free Subscription Tracker: the link is in the description.">Copy</button></li>
      <li><span>Before you go: our free Subscription Tracker shows every app you pay for. Link in the description.</span><button type="button" data-copytext="Before you go: our free Subscription Tracker shows every app you pay for. Link in the description.">Copy</button></li>
      <li><span>Paying for more apps than you think? Our free Subscription Tracker shows you. Link in the description and the pinned comment.</span><button type="button" data-copytext="Paying for more apps than you think? Our free Subscription Tracker shows you. Link in the description and the pinned comment.">Copy</button></li>
    </ul>
    <p class="outro-cards">End-card pictures (1920 × 1080, open and save): How To Rocket <a href="outro/end-card-htr-lexi.jpg" target="_blank" rel="noopener">Lexi</a> ·
      <a href="outro/end-card-htr-yuna.jpg" target="_blank" rel="noopener">Yuna</a> — Guide Glimpse <a href="outro/end-card-gg-hana.jpg" target="_blank" rel="noopener">Hana</a> ·
      <a href="outro/end-card-gg-ellie.jpg" target="_blank" rel="noopener">Ellie</a></p>
  </section>

<!--TOPICS-->
  <div class="bar">
    <input id="q" type="search" placeholder="Find a tool or a topic, e.g. Wise, budget, flights" aria-label="Find a tool or a topic" autocomplete="off">
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
  // To fix in YouTube Studio (Kevin, 15 Oct): titles (data/title-fixes.json) and game videos to move to Gaming
  // (data/game-category.json), for the manager; opens once a day while some are left.
  var TF = /*TITLE_FIXES*/, GF = /*GAME_FIXES*/, tf = document.getElementById("tf"), tfOpen = document.getElementById("tf-open");
  var CHANNEL = { htr: "How To Rocket", gg: "Guide Glimpse" }, tfDone = {}, gfDone = {};
  function loadDone(key, into) {
    try { JSON.parse(localStorage.getItem(key) || "[]").forEach(function (id) { into[id] = 1; }); } catch (e) {}
  }
  loadDone("tf-done", tfDone); loadDone("gf-done", gfDone);
  function left(list, done) { return list.filter(function (x) { return !done[x.id]; }).length; }
  function tfLeft() {
    var t = left(TF, tfDone), g = left(GF, gfDone);
    document.getElementById("tf-left").textContent = (t + g) + " left";
    document.querySelector("#tf-t-titles span").textContent = t;
    document.querySelector("#tf-t-games span").textContent = g;
    return t + g;
  }
  // One item: what to do (lines, with the copied text marked data-copied), Copy, Open in YouTube Studio, Done.
  function tfItem(x, done, key, meta, lines, copy) {
    var li = document.createElement("li");
    li.className = "tf-item" + (done[x.id] ? " done" : "");
    li.innerHTML = '<span class="tf-meta"></span>' + lines + '<div class="tf-do"><button type="button">Copy</button>' +
      '<a target="_blank" rel="noopener">Open in YouTube Studio ↗</a><label><input type="checkbox"> Done</label></div>';
    li.querySelector(".tf-meta").textContent = meta;
    li.querySelector("a").href = "https://studio.youtube.com/video/" + x.id + "/edit";
    var cb = li.querySelector("input");
    cb.checked = !!done[x.id];
    cb.addEventListener("change", function () {
      if (cb.checked) done[x.id] = 1; else delete done[x.id];
      li.classList.toggle("done", cb.checked);
      try { localStorage.setItem(key, JSON.stringify(Object.keys(done))); } catch (e) {}
      tfLeft();
    });
    li.querySelector("button").addEventListener("click", function (ev) {
      var t = li.querySelector("[data-copied]");
      copyText(copy, ev.currentTarget, function () {
        var r = document.createRange(); r.selectNodeContents(t);
        var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
      });
    });
    return li;
  }
  if ((TF.length || GF.length) && tf && tf.showModal) {
    var tfList = document.getElementById("tf-list"), gfList = document.getElementById("tf-glist");
    TF.forEach(function (x) {
      var li = tfItem(x, tfDone, "tf-done", CHANNEL[x.ch] + " · " + x.why,
        '<p class="tf-old"></p><p class="tf-new" data-copied></p>', x["new"]);
      li.querySelector(".tf-old").textContent = x.title;
      li.querySelector(".tf-new").textContent = x["new"];
      tfList.appendChild(li);
    });
    GF.forEach(function (x) {
      var li = tfItem(x, gfDone, "gf-done", CHANNEL[x.ch] + " · game video",
        '<p class="tf-title"></p><p class="tf-game">Category: Gaming · Game title: <b data-copied></b><span></span></p>', x.game);
      li.querySelector(".tf-title").textContent = x.title;
      li.querySelector("[data-copied]").textContent = x.game;
      li.querySelector(".tf-game span").textContent = x.note || "";
      gfList.appendChild(li);
    });
    var tabs = [["titles", TF], ["games", GF]];
    function showTab(name) {
      tabs.forEach(function (t) {
        document.getElementById("tf-t-" + t[0]).setAttribute("aria-selected", t[0] === name ? "true" : "false");
        document.getElementById("tf-p-" + t[0]).hidden = t[0] !== name;
      });
    }
    tabs.forEach(function (t) {
      var b = document.getElementById("tf-t-" + t[0]);
      b.hidden = !t[1].length;
      b.addEventListener("click", function () { showTab(t[0]); });
    });
    showTab(left(TF, tfDone) || !GF.length ? "titles" : "games");
    tfOpen.hidden = false;
    tfOpen.addEventListener("click", function () { tf.showModal(); });
    tf.querySelector(".tf-close").addEventListener("click", function () { tf.close(); });
    tf.addEventListener("click", function (ev) { if (ev.target === tf) tf.close(); });   // a click on the dark backdrop
    var today = new Date().toISOString().slice(0, 10), shown = null;
    try { shown = localStorage.getItem("tf-shown"); } catch (e) {}
    if (tfLeft() && shown !== today) {
      try { localStorage.setItem("tf-shown", today); } catch (e) {}
      tf.showModal();
    }
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
  // Ready topics: filter by tool or words
  var tq = document.getElementById("tq");
  if (tq) tq.addEventListener("input", function () {
    var s = tq.value.trim().toLowerCase();
    document.querySelectorAll("#topics .tp-group").forEach(function (g) {
      var any = false;
      g.querySelectorAll(".tp-tool").forEach(function (t) {
        var name = t.querySelector("b").textContent.toLowerCase(), hit = false;
        t.querySelectorAll("li").forEach(function (li) {
          var on = !s || name.indexOf(s) !== -1 || li.textContent.toLowerCase().indexOf(s) !== -1;
          li.hidden = !on; if (on) hit = true;
        });
        t.hidden = !hit; if (hit) any = true;
      });
      g.hidden = !any;
    });
  });
  only.addEventListener("change", filter);
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest("button[data-copy]");
    if (b) { copy(b); return; }
    var ct = ev.target.closest("button[data-copytext]");
    if (ct) { copyText(ct.dataset.copytext, ct, function () {
      var r = document.createRange(); r.selectNodeContents(ct.previousElementSibling);
      var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); }); return; }
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
    if (it.o) it.or = new RegExp(it.o, "i");   // link only on some of its videos (Skool: people who'd start a community)
    it.k.forEach(function (k) { keys.push({ k: k, it: it, rx: word(k) }); });
  });
  BOX.guides.forEach(function (g) { g.k.forEach(function (k) { gkeys.push({ k: k, g: g, rx: word(k) }); }); });
  keys.sort(function (a, b) { return b.k.length - a.k.length; });
  gkeys.sort(function (a, b) { return b.k.length - a.k.length; });

  // Topics (data/offer-topics.json, Kevin 29 Oct): a title that names none of our tools but a topic ("How to Create a
  // Budget From Scratch") gets the offers that fit it as suggestions to pick by hand. Same order as topic_matcher in
  // build-editor-lists.py: the most specific phrase, then a deal on our deals page, tools on the site, what a link is worth.
  function norm(s) { return s.toLowerCase().replace(/[’‘]/g, "'").replace(/[^a-z0-9']+/g, " ").trim(); }
  var topicItems = BOX.items.filter(function (it) { return it.tp; });
  topicItems.forEach(function (it) {
    var ps = [];
    it.tp.forEach(function (r) { ps = ps.concat(r.charAt(0) === "@" ? BOX.sets[r.slice(1)] || [] : [r]); });
    it.tps = ps;
  });
  function words(p) { return p.split(" ").length; }
  function topicFits(title) {
    var t = " " + norm(title) + " ", out = [];
    topicItems.forEach(function (it) {
      if (!chOk(it) || (it.or && !it.or.test(title))) return;
      var best = null;
      it.tps.forEach(function (p) {
        if ((t.indexOf(" " + p + " ") >= 0 || t.indexOf(" " + p + "s ") >= 0 || t.indexOf(" " + p + "es ") >= 0) &&
            (!best || words(p) > words(best))) best = p;
      });
      if (best) out.push({ it: it, p: best });
    });
    out.sort(function (a, b) {
      return words(b.p) - words(a.p) || b.it.dl - a.it.dl || b.it.st - a.it.st || b.it.v - a.it.v ||
        a.it.n.toLowerCase().localeCompare(b.it.n.toLowerCase());
    });
    return out;
  }

  // Words that are lowercase in a sentence ("How To Book Flight Ticket" -> "book flight ticket"); names keep their capitals.
  var COMMON = {};
  ("a an and or the to in on at of for from with by into onto over your my our their his her its this that these those it you " +
   "things thing know need should really worth price prices pricing features feature results result review reviews compared " +
   "comparison best manage protect connecting working loading opening showing sending downloading uploading playing " +
   "updating installing charging syncing signing logging " +
   "we they me him them i use using make create add remove delete change edit rename set setup get find fix turn off enable " +
   "disable install uninstall download upload update open close start stop share send receive transfer book order buy sell pay " +
   "cancel unsubscribe sign log login logout out back check see watch play join leave hide show block unblock connect disconnect opt " +
   "link unlink verify activate deactivate reset recover restore backup save print scan convert merge split crop cut trim rotate " +
   "resize compress translate write read apply claim redeem earn withdraw deposit top load register renew track search schedule " +
   "move copy paste import export sync stream cast mirror record take go run try put keep call text post like follow unfollow " +
   "invite accept reply pin unpin mute unmute archive lock unlock clear free new old account accounts app apps phone mobile " +
   "pc laptop computer browser video videos photo photos picture pictures image images screen chat chats " +
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
  BOX.common.split(" ").forEach(function (w) { COMMON[w] = 1; });   // the 7,600 most common English words (data/common-words.txt)
  var PROTECT = {};   // words of the app the video is about keep their capitals ("Box" in a Box video)
  // App names that are also everyday words keep their capital after these words: "in Word", "Google Drive", "MS Teams".
  var APPWORDS = { word: 1, teams: 1, edge: 1, keep: 1, drive: 1, photos: 1, sheets: 1, docs: 1, slides: 1, meet: 1, maps: 1,
                   music: 1, wallet: 1, pay: 1, lens: 1, calendar: 1, notes: 1, files: 1 };
  var BEFORE_APP = { "in": 1, on: 1, to: 1, from: 1, "with": 1, into: 1, google: 1, microsoft: 1, ms: 1, apple: 1, amazon: 1, samsung: 1 };
  var SHORT = { by: 1, "in": 1, on: 1, up: 1, to: 1, of: 1, no: 1, at: 1, or: 1, so: 1, as: 1, is: 1, it: 1, go: 1, "do": 1,
                my: 1, me: 1, we: 1, us: 1, be: 1 };
  function sentence(s) {
    var ws = s.split(/\s+/);
    return ws.map(function (w, i) {
      var lw = w.toLowerCase(), bare = lw.replace(/[^a-z']/g, "");
      // Only "Book" or "book" becomes "book"; "iPhone", "WhatsApp", "PC" and "I" stay as written.
      var plain = w === lw || (w.charAt(0) !== lw.charAt(0) && w.slice(1) === lw.slice(1));
      var app = APPWORDS[bare] && w !== lw && i > 0 && BEFORE_APP[ws[i - 1].toLowerCase().replace(/[^a-z]/g, "")];
      // "Opt-Out", "Step-by-Step" -> lowercase when every part is a common word; short parts only if they're little
      // words ("by", "in"), so names like "Wi-Fi", "U-Verse" and "K-Friends" stay as written
      if (w.indexOf("-") > 0 && !app && w.split("-").every(function (p) {
            var lp = p.toLowerCase(), b = lp.replace(/[^a-z']/g, "");
            return b && COMMON[b] && !PROTECT[b] && (b.length > 2 || SHORT[b]) &&
                   (p === lp || (p.charAt(0) !== lp.charAt(0) && p.slice(1) === lp.slice(1)));
          })) return lw;
      return COMMON[bare] && !PROTECT[bare] && !app && plain && w !== "I" ? lw : w;
    }).join(" ");
  }
  // The "how to" part ends where its brackets do: "Scanner (How to Opt-Out Right Now)" -> "Opt-Out Right Now".
  function balanced(s) {
    for (var i = 0, depth = 0; i < s.length; i++) {
      if (/[(\[]/.test(s.charAt(i))) depth++;
      else if (/[)\]]/.test(s.charAt(i))) { if (!depth) return s.slice(0, i).trim(); depth--; }
    }
    return s;
  }
  // "Kiwi.com" -> "Kiwi": YouTube turns names like that into links to the brand's site (without our code).
  function noTld(s) { return (s || "").replace(/\b([A-Za-z0-9-]+)\.(com|io|net|ai|app|co|org|me|tv|gg|ph|in|uk)\b/gi, "$1"); }
  function trimFiller(a) {
    var rx = /\s+(full guide|step by step( guide)?|complete guide|tutorial|guide|easy|easily|quick|quickly|fast|for beginners|beginners?'?s? guide|in \d+ (seconds|minutes|steps)|((in|for) )?20\d\d|new update|update|latest|simple|\(.*\)|\[.*\])$/i, prev;
    a = a.replace(/[\s,.!?:;-]+$/, "");
    do { prev = a; a = a.replace(rx, "").replace(/[\s,.!?:;-]+$/, ""); } while (a !== prev);
    return a;
  }
  // The "A vs B" part of a title's parts ("… Earnings (Fiverr Pro vs Fiverr)" -> "Fiverr Pro vs Fiverr"), if any.
  function vsPart(segs) {
    var s = segs.filter(function (x) { return /\svs\.?\s/i.test(x); })[0], m = s && s.match(/\(([^()]*\svs\.?\s[^()]*)\)/i);
    return m ? m[1] : s;
  }
  // The compared names from the "A vs B" part; with cmp (our tools the title compares), a part that runs on becomes the
  // tool's name ("Temu Which One Is Worth It" -> "Temu"), and a messy one switches to the tools' names altogether.
  function vsNames(vs, cmp) {
    var p = vs.split(/\s+vs\.?\s+/i).map(function (x) { return noTld(trimFiller(x.trim())); }).filter(Boolean).slice(0, 3);
    if (!cmp || cmp.length < 2) return p;
    var names = cmp.map(function (x) { return noTld(x.n); });
    p = p.map(function (x) {   // "Fiverr Pro" stays "Fiverr Pro" (a name itself); otherwise the longest name it starts with
      var lx = x.toLowerCase();
      if (names.some(function (n) { return n.toLowerCase() === lx; })) return x;
      return names.filter(function (n) { return lx.indexOf(n.toLowerCase() + " ") === 0; })
        .sort(function (a, b) { return b.length - a.length; })[0] || x;
    });
    return p.some(function (x) { return x.split(/\s+/).length > 4; }) ? names : p;
  }
  // The first line of the pinned comment: one friendly question about the video that invites a reply, nothing beyond
  // the title (rules of the pinned lists, 9 Oct). The editor can change it before copying.
  function question(title, subj, cmp) {
    var t = title.replace(SUFFIX, "").trim(), low = t.toLowerCase(), S = noTld(subj), h = 0, i;
    for (i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) >>> 0;
    var pick = function (a) { return a[h % a.length]; };
    if (/crack|keygen|license key|mod apk|modded|hack|cheat|unlocked|trial reset|activator|free premium|premium (for )?free|lifetime free|free lifetime/.test(low))
      return "Stay safe: skip cracked apps and “free premium” offers." + (S ? " Questions about " + S + "? Ask below 👇" : " Ask your questions below 👇");
    var segs = t.split(/\s+[-–—|:]\s+|\s*\|\s*|:\s+/);
    var vs = vsPart(segs);
    if (vs) {
      var p = vsNames(vs, cmp);
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
    segs.forEach(function (s) { var m = !how && s.match(/how\s+to\s+(.+)/i); if (m) how = balanced(m[1]); });
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

  // The description: one sentence that extends the title, without promising what the video shows (Kevin, 13 Oct: "short,
  // not overpromising, just as extension of the title", so viewers aren't pulled away from our links).
  var SAFETY = /crack|keygen|license key|mod apk|modded|hack|cheat|unlocked|trial reset|activator|free premium|premium (for )?free|lifetime free|free lifetime/;
  function lowerFirst(s) {   // "Pros, cons" -> "pros, cons", but the tool's name keeps its capital ("Fiverr Pro to Fiverr")
    return /^[A-Z][a-z]/.test(s) && !PROTECT[s.split(/\s/)[0].toLowerCase().replace(/[^a-z']/g, "")] ? s.charAt(0).toLowerCase() + s.slice(1) : s;
  }
  function extend(title, subj, cmp) {
    var t = noTld(title.replace(SUFFIX, "").trim()), low = t.toLowerCase(), S = noTld(subj);
    if (SAFETY.test(low)) return "Stay safe: skip cracked apps and “free premium” offers.";
    var segs = t.split(/\s+[-–—|:]\s+|\s*\|\s*|:\s+/).map(function (x) { return x.trim(); }).filter(Boolean);
    var vs = vsPart(segs);
    if (vs) {
      var p = vsNames(vs, cmp);
      if (p.length >= 2) {
        var more = segs.filter(function (x) { return x !== vs && !/compar|\bvs\b/i.test(x.replace(/compared$/i, "")); })
          .map(function (x) { return trimFiller(sentence(x)).replace(/\s*compared$/i, ""); }).filter(Boolean).join(", ");
        return (p.length === 2 ? p[0] + " or " + p[1] : p[0] + ", " + p[1] + " or " + p[2]) + "? This video compares them" +
               (more ? ": " + lowerFirst(more) : "") + ".";
      }
    }
    var how = null;
    segs.forEach(function (x) { var m = !how && x.match(/how\s+to\s+(.+)/i); if (m) how = balanced(m[1]); });
    if (!how && /not working|error|\bfix\b|problem|issue|can'?t|won'?t|failed|stuck/.test(low))
      return trimFiller(sentence(segs[0])).replace(/\s*-?\s*fix(ed)?$/i, "") + "? This video shows what to do.";
    if (!how && /review|worth it|honest|tested/.test(low)) {
      var subject = S || trimFiller(segs[0].replace(/\b(honest )?review\b.*$/i, "").trim());
      var r = lowerFirst(segs.slice(1).map(function (x) { return trimFiller(sentence(x)); }).filter(Boolean).join(", "));
      var ask = /^(is|are|does|do|can|should|which|what|how|why|will)\b/i.test(r);
      return (subject ? "Thinking about " + subject + "? " : "") + "This video is our review" + (r ? ": " + r + (ask ? "?" : ".") : ".");
    }
    if (how) { var a = sentence(trimFiller(how)); if (a) return "This video shows how to " + a + "."; }
    return sentence(trimFiller(segs.join(": "))) + ".";
  }
  // The sentence starts with a capital ("best Proton VPN settings" -> "Best ..."); names like "iPhone" or "eBay" stay.
  function capFirst(s) {
    var m = s.match(/^[a-z][a-z'-]*(?![A-Za-z])/);
    return m && m[0].split("-").every(function (p) { return COMMON[p] || COMMON[p.replace(/'s$/, "")] || SHORT[p]; })
      ? s.charAt(0).toUpperCase() + s.slice(1) : s;
  }
  function closing(aff) {
    return "❤️ If this helped, please like and subscribe!" + (aff ? " Some links earn us a small commission at no extra cost to you." : "") + " Thanks!";
  }
  // A longer description (Kevin, 29 Oct: "the description should be a bit longer"; the uploaders write theirs with an AI
  // and had moved our link into the middle as "🔗 Get …"): a prompt that keeps our lines on top and the 13 Oct rule (no
  // promises beyond the title).
  function aiPrompt(title, links, aff) {
    return ["Write a YouTube video description for this video: " + title.replace(SUFFIX, "").trim(), "",
      "Start with these lines, copied exactly, each on its own line:"].concat(links, [NEWS, "",
      "Then an empty line and 2 or 3 short paragraphs (about 150 words in total) in simple English: what the video " +
      "helps with and who it is for. Use the words people search for.",
      "Only say what the title says: don't invent steps, features, prices or results, and don't write \"best\", \"#1\" " +
      "or \"guaranteed\". No other links or web addresses, and no \"🔗\" lines.",
      "End with this line, copied exactly:", closing(aff)]).join("\n");
  }
  // A video plan for any title (Kevin, 29 Oct: "give the editors ideas how to structure the video ... for affiliates we
  // use or how we present them the best way for the user ... all titles that have no clear app"): the viewer's problem
  // first, then at most one of our offers where it really helps, with the spoken affiliate note; none on cancel, refund
  // or "free" videos (our rule). Offers: the title's tools, else its topic fits, else every tool on the site.
  var OUTRO = "Want to see what all your subscriptions cost? Get our free Subscription Tracker: the link is in the description.";
  function planPrompt(title, its, fits, noOffer) {
    var t = title.replace(SUFFIX, "").trim(), list, offer;
    var say = "say once: \"The link is in the description. It's an affiliate link, so we may earn a small commission " +
              "at no extra cost to you.\"";
    var line = function (it) { return "- " + it.n + ": " + it.d; };
    if (noOffer) offer = "No product or affiliate offer in this video (our rule for this kind of title).";
    else if (its.length) offer = "The video is about " + names(its) + ". Show it in use. Where it fits naturally (for " +
      "example right after the main steps), " + say;
    else {
      list = fits.length ? fits.slice(0, 6).map(function (f) { return f.it; })
           : BOX.items.filter(function (it) { return it.st && chOk(it); });
      offer = (fits.length ? "These tools we link to fit the topic" : "These are the tools we link to") + " (name: what " +
        "it is):\n" + list.map(line).join("\n") + "\nIf one of them genuinely helps viewers with this exact problem, " +
        "add ONE short scene for it as a tip after the main steps, never instead of the real answer, and " + say +
        " If none really fits, leave it out: a forced product mention costs trust.";
    }
    return ["Plan a short YouTube tutorial (2 to 4 minutes, like our other videos) for this title: " + t, "",
      "Write it as numbered scenes. For each scene: what to show on screen and what to say (one or two sentences).",
      "1. Hook (first 10 seconds): show the problem from the title and say what the viewer will be able to do.",
      "2. The quick answer first, then the steps in the order the viewer does them.",
      "3. What to do if it doesn't work: common mistakes and other options.",
      "4. Offer: " + offer,
      "5. Outro: \"" + OUTRO + "\"", "",
      "Rules: help the viewer first and keep it specific to this title, no filler. Only things that are true for this " +
      "topic; if a step depends on the app version, the country or the bank, say so. Don't promise results, and don't " +
      "say \"best\", \"#1\" or \"guaranteed\".",
      "At the end, name in one line the tool you used in scene 4 (or \"none\")."].join("\n");
  }

  var vt = document.getElementById("vt"), sel = document.getElementById("vtool"), made = document.getElementById("made");
  var vstatus = document.getElementById("vstatus"), onlytop = document.getElementById("onlytop");
  var pin = document.getElementById("pin"), desc = document.getElementById("desc"), vnote = document.getElementById("vnote");
  var vtopics = document.getElementById("vtopics"), aiprompt = document.getElementById("aiprompt"), MAX_TOPICS = 8;
  var planprompt = document.getElementById("planprompt");
  // Links for one channel only (FlexOffers: How To Rocket): the Channel row shows while there are any, and they're
  // offered only once that channel is picked (the choice stays on this device).
  var vch = document.getElementById("vch"), CH = { htr: "How To Rocket", gg: "Guide Glimpse", lp: "Logic Protocol" };
  if (BOX.items.some(function (it) { return it.c; })) document.getElementById("vchrow").hidden = false;
  try { vch.value = localStorage.getItem("team-links-channel") || ""; } catch (e) {}
  function chOk(it) { return !it.c || it.c === vch.value; }
  var none = document.createElement("option"); none.value = ""; none.textContent = "No link (newsletter line only)"; sel.appendChild(none);
  BOX.items.forEach(function (it) {
    var o = document.createElement("option"); o.value = it.s; o.textContent = it.n + (it.c ? " (" + CH[it.c] + " only)" : ""); sel.appendChild(o);
  });
  var manual = null;
  // The tool a text names (longest name first), as in the editor lists; [] if none. With onlyRule, the tool whose link
  // the title names but whose rule leaves it out (Skool on a settings video, a How To Rocket-only link on another channel).
  function toolIn(text, title, onlyRule) {
    var tl = " " + text.toLowerCase() + " ", j, it;
    for (j = 0; j < keys.length; j++) {
      it = keys[j].it;
      if (!keys[j].rx.test(tl) || (it.xr && it.xr.test(title))) continue;
      if ((!it.or || it.or.test(title)) && chOk(it)) { if (!onlyRule) return [it]; }
      else if (onlyRule) return [it];
    }
    return [];
  }
  // "A vs B (vs C)": every compared tool we have a link for, in the title's order (one 👉 line each, like the editor lists).
  function compared(title) {
    var vs = vsPart(title.split(/\s+[-–—|:]\s+|\s*\|\s*|:\s+/)), out = [];
    if (vs) vs.split(/\s+vs\.?\s+/i).slice(0, 3).forEach(function (part) {
      var t = toolIn(part, title)[0];
      if (t && out.indexOf(t) < 0) out.push(t);
    });
    return out;
  }
  function names(its) {
    var n = its.map(function (x) { return x.n; });
    return n.length > 1 ? n.slice(0, -1).join(", ") + " and " + n[n.length - 1] : n.join("");
  }
  function makeLines() {
    var title = vt.value.trim();
    made.hidden = !title;
    if (!title) return;
    var tl = " " + title.toLowerCase() + " ", its = [], it, guide = null, note, j, ruled = null;
    var cancel = CANCEL.test(title), excluded = !cancel && EXCLUDE.test(title);
    // Topic suggestions only for a title that names none of our tools (a Skool settings video names one)
    var named = !cancel && !excluded && (compared(title).length > 1 || toolIn(title, title).length || toolIn(title, title, true).length);
    var fits = cancel || excluded || named || SAFETY.test(title.toLowerCase()) ? [] : topicFits(title);
    if (cancel) {
      for (j = 0; j < gkeys.length && !guide; j++) if (gkeys[j].rx.test(tl)) guide = gkeys[j].g;
      note = "";
    } else if (excluded) {
      note = "";
    } else if (manual !== null) {
      if (bySlug[manual] && chOk(bySlug[manual])) its = [bySlug[manual]];
      else if (bySlug[manual]) ruled = bySlug[manual];
      note = its.length ? "Picked by hand." : ruled ? "" : "No link: newsletter line only.";
    } else {
      its = compared(title);
      if (its.length < 2) its = toolIn(title, title);
      if (!its.length) ruled = toolIn(title, title, true)[0] || null;
      note = its.length > 1 ? "Found in the title. To use only one, pick it here."
           : its.length ? "Found in the title. Wrong one? Pick another."
           : ruled && !chOk(ruled) ? ""
           : ruled ? "If this video is for people starting out, pick " + ruled.n + " here."
           : fits.length ? ""
           : "No tool from our list in the title. Pick one if the video is about one.";
    }
    it = its[0] || null;
    sel.value = it ? it.s : ruled && manual === ruled.s ? manual : "";
    sel.disabled = cancel || excluded;
    PROTECT = {};
    (its.length ? names(its) : guide ? guide.n : "").toLowerCase().split(/[^a-z0-9']+/).forEach(function (w) { if (w) PROTECT[w] = 1; });
    var links = guide ? ["👉 Step-by-step guide: subscriptionchef.app/cancel/" + guide.s]
              : its.map(function (x) { return "👉 Try " + x.w + " (affiliate): " + (x.u || "useandlike.com/" + x.s); });
    var subj = it ? it.n : guide ? guide.n : "";
    var cmp = its.length > 1 ? its : null;   // a comparison of our tools: their clean names for the question and sentence
    pin.value = [question(title, subj, cmp)].concat(links, [BOX.pinNews]).join("\n");
    var top = links.concat([NEWS]).filter(Boolean).join("\n");
    desc.value = onlytop.checked ? top : top + "\n\n" + capFirst(extend(title, subj, cmp)) + "\n\n" + closing(!!it);
    aiprompt.value = aiPrompt(title, links, !!it);
    planprompt.value = planPrompt(title, its, fits, cancel || excluded || !!ruled || SAFETY.test(title.toLowerCase()));
    vnote.textContent = note;
    showTopics(fits);
    vstatus.className = "vstatus" + (it ? " yes" : cancel || excluded || ruled ? " warn" : "");
    vstatus.textContent = its.length > 1 ? "✓ We have affiliate links for " + names(its) + ": one 👉 line each."
      : it ? "✓ We have an affiliate link: " + it.n + " → " + (it.u || "useandlike.com/" + it.s)
      : fits.length && manual === null ? "No app from our list in the title, but " + (fits.length === 1 ? "one of our offers fits" :
          fits.length + " of our offers fit") + " its topic. Pick one only if it really fits the video:"
      : cancel ? "Cancel video: no affiliate link" + (guide ? ", the cancel guide goes in instead" : "") + " (our rule)."
      : excluded ? "No affiliate link: video about refunds, free versions, cracks or alternatives (our rule)."
      : ruled && !chOk(ruled) ? "Our " + ruled.n + " link is only for " + CH[ruled.c] + " videos" +
          (vch.value ? ", so this one gets only the newsletter line." : ". Is this one? Pick the channel above.")
      : ruled ? "No affiliate link on this one (our rule for " + ruled.n + "): " + lowerFirst(ruled.on)
      : "No affiliate link for this video: only the newsletter line.";
    grow(pin); grow(desc); grow(aiprompt); grow(planprompt);
  }
  // The suggested offers as buttons (the first MAX_TOPICS; "All N" shows the rest in the list below via its search).
  function showTopics(fits) {
    vtopics.textContent = "";
    vtopics.hidden = !fits.length;
    if (!fits.length) return;
    var b = document.createElement("b");
    b.textContent = "Fits the topic:";
    vtopics.appendChild(b);
    fits.slice(0, MAX_TOPICS).forEach(function (f) {
      var c = document.createElement("button");
      c.type = "button"; c.dataset.topic = f.it.s; c.textContent = f.it.n; c.title = "Topic: " + f.p;
      c.setAttribute("aria-pressed", manual === f.it.s ? "true" : "false");
      vtopics.appendChild(c);
    });
    if (fits.length > MAX_TOPICS) {
      var a = document.createElement("button");
      a.type = "button"; a.className = "all"; a.dataset.all = fits[0].p; a.textContent = "All " + fits.length + " ›";
      vtopics.appendChild(a);
    }
  }
  vtopics.addEventListener("click", function (ev) {
    var c = ev.target.closest("button");
    if (!c) return;
    if (c.dataset.topic) { manual = manual === c.dataset.topic ? null : c.dataset.topic; makeLines(); return; }
    q.value = c.dataset.all; filter();   // every fitting offer in the list below, each with its Copy button
    q.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });
  function grow(ta) { ta.style.height = "auto"; ta.style.height = ta.scrollHeight + 2 + "px"; }   // whole text visible on phones
  pin.addEventListener("input", function () { grow(pin); });
  desc.addEventListener("input", function () { grow(desc); });
  aiprompt.addEventListener("input", function () { grow(aiprompt); });
  planprompt.addEventListener("input", function () { grow(planprompt); });
  vt.addEventListener("input", function () { manual = null; makeLines(); });
  onlytop.addEventListener("change", makeLines);
  vch.addEventListener("change", function () {
    try { localStorage.setItem("team-links-channel", vch.value); } catch (e) {}
    makeLines();
  });
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

    lines_for = make_matcher(tools, read_links(tools))
    code = {v: k for k, v in CHANNEL_NAMES.items()}   # "How To Rocket" -> "htr" (links for one channel only)
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
        kind, lines = lines_for(title, code.get(channel))
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
