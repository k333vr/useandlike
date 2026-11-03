# useandlike.com — notes for Claude

The owner is a beginner. Explain things in plain language and do as much as possible yourself.

## The site
- `index.html` (CSS and JS inline): the home page (since 1 Nov 2026 the app news front page, see App news below), the
  Videos tab and the small # pages (join, welcome, privacy, tracker, thanks).
  Plus real pages made by `node scripts/build-pages.js` from the EDIT HERE block and videos.js (since 11 Oct 2026):
  `category/<name>/`, `tool/<slug>/`, `about/`, `how-we-choose/`, `how-we-make-money/`, `work-with-us/`, `sitemap.xml`,
  `robots.txt`; plus the hidden `team-links/` page from `scripts/build-editor-lists.py`. The generated files are committed (Cloudflare has no build step). It also refreshes two marked blocks in
  index.html (`build-pages:ld` structured data, `build-pages:home` the category list as plain HTML for crawlers that
  don't run JavaScript). No frameworks, no tracking scripts, no external requests (except Beehiiv's signup form, see NEWSLETTER).
- Deals page `deals/` (29 Oct 2026, Kevin: deals we promoted keep earning while they run; the newsletter's deal row gets
  a "+ more deals" strip pointing here): made by build-pages.js from `data/deals.json`, icons `img/deals/<slug>.webp`
  (96x96, the brand's own app icon), "Deals" in the header nav. Only offers checked on the brand's own website, with
  that date in `checked`; take a deal out as soon as it ends (check.js warns after 7 days, fails on a missing short
  link or a FlexOffers link). Each card: Get the deal -> /slug (sponsored), About -> the tool page.
  Under them (1 Nov 2026, Kevin: "only 7 deals listed ... when we have like 1000s of partners"): "More offers from our
  partners", one line per brand with filter chips by group, from `data/partner-offers.json`, written by
  `scripts/partner-offers.py` from the Studio's deal tracker (the brands' own listings on Yazing, seen in the last 3 days;
  every daily news run refreshes it). It drops out-of-season and old offers, non-offers, superlatives, undercutting lines,
  FlexOffers/direct/paused links and brands with a checked deal; the page says they're the brands' listings and the day
  we saw them. Don't edit the JSON by hand; check.js fails on a bad link and warns when the list is over 3 days old.
- After changing the EDIT HERE block, videos.js or the small pages' texts (`PAGES` at the top of scripts/build-pages.js):
  run `node scripts/build-pages.js` (build-videos.py runs it too). check.js fails while the pages are out of date.
- Hosted on Cloudflare as a Worker named `useandlike` with static assets (Workers Builds, connected to GitHub).
  Pushing to `main` deploys to useandlike.com. Build results show as the "Workers Builds: useandlike"
  check on each commit (`gh api repos/k333vr/useandlike/commits/<sha>/check-runs`).
  Push changes to `main` ONLY. Never push the same commit to another branch: Cloudflare then builds it once as
  a branch preview (`npx wrangler preview`, which hangs at "Initializing" and times out) and skips the `main`
  build, so the site does not update (this happened on 3 Oct 2026 until main-only pushes).
  Do NOT add a `wrangler.jsonc`: Cloudflare's dashboard settings build this repo without one, and adding
  one made production builds fail (commits 274c3d1, de405a4). Re-add only after seeing the build log.
  Test locally from OUTSIDE the repo (wrangler keeps a .wrangler folder in the current folder; inside the repo it
  reloads endlessly): `cd /tmp && CLOUDFLARE_CF_FETCH_ENABLED=false npx wrangler dev --assets /home/user/useandlike` (serves `_redirects` too).
- All editable content is in the `EDIT HERE` block at the top of `index.html`:
  `CHANNELS`, `NEWSLETTER`, `OPEN_IN_NEW_TAB`, `VISIBLE_COUNT`, `CATEGORIES`, `TOOLS`, `VIDEOS`.
- `NEWSLETTER.ready` shows the signup at the top of every page, on #join, and a box on home and category pages. With `beehiivForm` (the `data-beehiiv-form` id from Beehiiv's embed code) it loads Beehiiv's script `subscribe-forms.beehiiv.com/v3/loader.js`, which shows Beehiiv's own field (an iframe) where the signup is; this is the one allowed external request (owner's choice). Without it, the button opens the Beehiiv signup page via `/newsletter`. Beehiiv's separate attribution.js is not needed (the loader includes it). Double opt-in is on (owner is in Austria); Beehiiv's "Opt-in redirect URL" is `useandlike.com/welcome` -> `#welcome` (INFO page with `img/welcome.webp` and the tracker button), so `/welcome` must stay in `_redirects`. Posting our own form to Beehiiv's /create is blocked ("Forbidden"), so don't. `/newsletter` must stay in `_redirects` (the check script enforces it).
  Subscribers see no box and no header field, and their browser loads nothing from Beehiiv (Kevin, 2 Nov: "remove it
  when it sees you are already subscribed"): Beehiiv's `bhv_*_subscribed` cookie, or `localStorage` "ul-subscribed",
  set on #welcome / #thanks / #tracker or by the box's "Already subscribed? Hide this" (index.html and build-pages.js'
  SCRIPT + beehiivHead; the privacy page says so). The #join page keeps its field. The front page's story list ends
  with a "More stories" button to /news/.
- All news page `/news/` (Kevin, 3 Nov: "2 or 3" per row, "in between we can add deals"): story cards in a grid
  (`.srows.grid3`: 1 column on phones, 2 from 700 px, 3 from 980 px), and after every `NEWS_DEAL_EVERY` (9) stories a
  row of 4 deals (`newsWithDeals` in build-pages.js): the checked deals first, then partners' own offers
  (`partnerMini`, labelled as their listing), mixed across groups; then a block of 8 one-liners ("In one line").
  One-liners (Kevin, 3 Nov: yes to "short items" for the rest of the day's news): the daily run turns every real-news
  candidate it doesn't write in full into a `quick` story (NEWS.md); their pages are `noindex` and out of the sitemap,
  the RSS feed has full stories only, the front page shows 6.
- Google (Kevin, 3 Nov: "google search viewers are worth a lot"): `sitemap.xml` gives story pages a `<lastmod>`;
  `news-sitemap.xml` (Google News format) lists the full stories that went up on the newest day and the day before;
  robots.txt names both. Search Console only counts visitors from Google searches.
- No display ads, whatever the traffic (Kevin, 3 Nov: "we stick with that regardless of visitor amount"): affiliate
  links, brand deals and our own offers only (ads would need a cookie banner, slow the site and pull clicks away).
- Layout: until 1 Nov 2026 the home page was the category list (Craigslist-style). Kevin, 1 Nov ("overall way better",
  "go"): the home page is app news; `/how-tos/` is a search over all our videos (`how-tos/search.json`, loaded on the
  first search: every non-Short video of data/channel-videos.tsv, the tools, stories, checked deals and partner offers),
  then "How-tos people watch" and one quiet line of category links (Kevin, 1 Nov: the big category grid with the tool
  links "doesn't look clean enough maybe have just the search bar"; the grid is gone). Nav:
  News (/) · How-tos · Videos (#videos) · Deals. A category heading opens its
  category page (`/category/web-hosting/`): each tool with `description`, optional `why`/`details`, "Our pick", a
  Visit button and a link to its tool page, then our videos about the category. A tool page (`/tool/wise/`): what it
  does, Visit button, all our videos about it ("Show all" after 24), the category's other tools. Old links
  (`useandlike.com/#web-hosting`, `#about`) forward to the real pages. Tool pages with fewer than 3 videos and no
  `why`/`details` (and thin categories) are `noindex` and stay out of the sitemap until they have more.
- Tool fields: `name`, `category`, `description`, `slug` (short link), `isPick`; optional `why`, `details`.
- App news (1 Nov 2026, Kevin: "no limit ... a lot of newcomer apps ... everything thats worth reporting"): one file per
  story, `data/news/<slug>.json` (the slug is the page address `/news/<slug>/`; never rename it). Fields: `slug`, `date`
  (YYYY-MM-DD), `head`, `dek` (what happened, our words; doesn't repeat the headline), `sources` [{name, url}] (required);
  optional `topic`, `tag`, `means` ("What it means for you"), `todo` ("What to do"), `details`, `where`, `image`/`thumb`
  (2:1, ours only, e.g. the newsletter cards in img/nl/), `apps`, `howtos` (video ids), `category`, `video` (our news
  video's YouTube id), `rank` (1 = lead on its day), `quick` (one-liner), `rumor` (rumor, leak or feature in testing:
  amber tag + "Not confirmed" note; Kevin, 1 Nov: speculative stories welcome when framed as such), `item`/`items`
  (Studio story ids), `checked`.
  Facts only from the named sources, neutral words, no superlatives (check.js scans the story pages). How to write one
  and the daily run: NEWS.md (`scripts/news-intake.py todo` lists the Studio's candidates not yet on the site; routine
  "Use & Like daily news pages" writes, builds, checks and pushes every morning). Each full story also gets a presenter
  script in the Studio (`scripts/news-scripts.py save`, NEWS.md "Scripts for the presenter"): versions A/B/C, `takes`
  (her opinion lines: bold is fine, never a twisted fact), `points` (3-6 key points for the teleprompter's Key points
  mode), no spoken call to action; she reads them on scripts.useandlike.com (useandlike-ops/studio). build-pages.js makes the story pages
  (NewsArticle structured data), `/news/`, `/news/feed.xml` (RSS) and the front page (lead = the newest rank-1 story of
  the last 3 days; a story without its own picture shows its apps' App Store icons on the first app's colour:
  `scripts/app-icons.py` -> `img/apps/<slug>.webp` + `data/app-icons.json`, Kevin 1 Nov: "looks strange just with the letters";
  later: "combine them with the app logos we already have for the thumbnails but still changeable on click": Kevin's pick in
  the Studio's Icons tab (studio.useandlike.com/#icons, table app_icons, applied on the next daily run) wins, then the
  thumbnail tool's saved logo (tngg.app's D1 `tngg-studio` + R2, read only), then the App Store; each run re-checks for new logos;
  devices and systems (iPhone, Apple Watch, macOS, Pixel Watch, Windows 11) show their maker's logo (`MAKERS` in
  app-icons.py; Apple: `data/makers/apple.png`; Kevin, 2 Nov: the Apple Watch top story showed "just an A not Apple logo");
  since 3 Nov also Samsung/Galaxy/One UI, Android (Auto, TV, XR, numbers) and Nothing/CMF (`data/makers/samsung.png`,
  `android.png`, `nothing.png`: the App Store had matched Shop Samsung, Android Switch and a cake shop; the Studio's news
  thumbnails copy these logos, so a wrong one shows twice);
  latest news beside the checked deals, newsletter box via
  `[data-join]`, one-liners, how-tos). Recommended how-tos everywhere: only videos with a new thumbnail
  (`data/new-thumbs.json`, refreshed by useandlike-ops/analysis/new-thumbs-sync.py) and never cancel/refund/"free" titles.
- Story pictures (2 Nov 2026, Kevin on the examples: "the story designs are also fire, that's how it should also look on
  the website"): `node scripts/story-pictures.js` (daily news run, after app-icons.py, before build-pages.js) draws per
  story `img/stories/<slug>.jpg` (1200x630 share picture with tag + headline: og:image, twitter large card, Google
  Discover via `max-image-preview:large`), `<slug>-art.jpg` (1200x600 without words: story page picture and front page
  lead) and `<slug>-thumb.jpg` (320x160, story lists), plus `img/share/default.jpg` (every other page; the home page has
  its own share tags in index.html's head). Look: the app icon(s) on the app's colour inside royal blue, glassy tiles,
  gold mark. Only new or changed stories are drawn (fingerprint in `data/story-pictures.json`, also the `?v=` of the
  links); pictures of deleted stories are removed. A story's own `image` still wins on the page. check.js fails on a
  share picture that doesn't exist and warns about a story without pictures. Fonts: Gelasio + Inter from
  ../useandlike-ops/analysis/newsletter/cards/.fonts, else downloaded once to ~/.cache/useandlike-fonts.
  Logo size (Kevin's picks, 2 Nov): about 64% of the story picture's height, 88% of the list picture's.
  Top-story picture (2 Nov, Kevin: options 1, 2, 4, 5 and 7, "switch between those and track traffic a b test it later"):
  for rank-1 stories story-pictures.js also draws `-lead2.jpg` (1200x400 band: logo, app name, tag), `-lead4.jpg`
  (1200x600: a presenter beside the logo; 16 ladies and outfits in `img/presenters/`, listed in `data/presenters.json`,
  one per story; entries with `"kind": "bust"` are close-ups with a `mood` for the news video thumbnails and are left out
  here) and `-lead7.jpg` (1200x400 "Today in apps"); 1 is `-art`, 5 the share picture. The front page shows one
  per top story, rotating by the story's date (`LEAD_STYLE` in build-pages.js: "" rotates, "4" keeps style 4); the lead
  section carries `data-lead-style` for a later A/B test.
  Cards (2 Nov, later; Kevin: the boxes felt "cut off or not fitting", picked "D + D"): the home page's top story and every
  story list show the app's logo on its own (`appMark` in build-pages.js; a second app small on its corner, a letter
  when there's no logo) on a card in a soft tint of the app's colour (`--c` per card, CSS `.srows li`, `.lead-story.card`,
  mixed with `--surface`, so dark mode works). The picture styles above are still drawn, unused for now (kept for an A/B
  test); story pages keep their `-art.jpg` picture. Kevin's later idea: rank stories by clicks once there are enough.
  The front page's top story shows only its `dek`, and on phones only the dek's first sentence (Kevin, 2 Nov: "nobody
  likes clutter or wall of texts"); write the dek's first sentence so it tells the story on its own.
- Look (2 Nov 2026, Kevin picked "white + gold" from 5 looks; silver and our blue may come into some elements later):
  white background, gold lines: `--rule` (the line above each section), `--rule-soft` (menu and footer lines), `--line`
  (card borders and row lines, light gold); dark mode keeps its colours with muted gold lines.
- Counted links (1 Nov 2026, Kevin: "maybe we can track those or highlight A b test them"): the footer's About / How
  we choose / How we make money / Work with us go through `/c-about`, `/c-choose`, `/c-money`, `/c-work` (block
  "# Counted site links" in _redirects), so Cloudflare counts clicks as totals. A/B test: the "Run an app or a brand?"
  strip (`#wwu`, link `/c-work-strip`) shows on about half of all page views, picked fresh each time (Math.random, nothing
  stored; the privacy page says so); on those page views the footer's Work with us link becomes `/c-work-b`. Version A
  = /c-work clicks, version B = /c-work-b + /c-work-strip, each per half of the page views:
  `python3 ../useandlike-ops/analysis/site-links.py 14` (also in the Monday report).
- Channel videos: `videos.js` (generated, ~2,250 videos about our tools) is loaded only when the Videos tab opens;
  the category and tool pages list the same videos as plain HTML.
  Refresh: `scripts/fetch-videos.sh` (yt-dlp, all videos of the 3 channels -> `data/channel-videos.tsv`), then
  `python3 scripts/build-videos.py` (matches titles to TOOLS, drops Shorts and titles like cancel/refund/delete account/free alternative
  and other products with the same name (NOT_ABOUT, e.g. Nolo VR, WiseCleaner), downloads missing thumbnails, rebuilds the pages). Re-run build-videos.py after adding or renaming a tool. Videos tab pages 24 at a time.
  After a batch of new thumbnails on YouTube: `python3 scripts/build-videos.py --refresh-thumbs` downloads every
  thumbnail again and rewrites only the ones that changed (1 Nov 2026: 790, 777 of them from the thumbnail tool; Kevin:
  the new ones "look better", and shelves of recommended how-tos use only videos with a new thumbnail).
- `VIDEOS` (hand-picked, shown first) feeds the Videos tab too: `{ title, url, channel, category, tool? }` (url = youtube.com/watch?v=<11-char id>).
  Each video needs a thumbnail at `thumbs/<id>.jpg` (320x180, from https://i.ytimg.com/vi/<id>/mqdefault.jpg),
  so the site makes no requests to YouTube. The Videos tab shows category buttons (side list on wide screens)
  and a card grid; tools without videos get "Search on:" links per channel. `#videos` = all, `#videos-email` = one category.
  Leave out video titles that undercut the affiliate offer ("premium for free", "license key", "trial reset", "free alternative").
- Editor lists: `python3 scripts/build-editor-lists.py` -> `editors/` (tool-links.csv, videos-<channel>.csv with the lines to paste;
  not published). It also writes `team-links/index.html`, the team's links page (Copy button per 👉 line, date added,
  what's new/removed, and a box: paste a new video's title, see whether we have an affiliate link, get the pinned comment
  (question + 👉 + 📩) and a short description: our lines first, one sentence that extends the title without promising
  what the video shows, the closing line (Kevin, 13 Oct: short, no overpromising, nothing that pulls clicks away from our
  links); same title rules as the editor lists; data/common-words.txt keeps the sentences in normal case) at useandlike.com/team-links/: a hidden page Kevin shares with the manager and uploaders (not
  linked anywhere, noindex, not in the sitemap). Commit it with every link change so it stays current. `scripts/youtube-descriptions.py` (login/run, preview by default, `--apply` to change YouTube) puts the same
  lines at the top of old descriptions via the YouTube Data API, most viewed first, ~180/day; tokens live outside the repo.
  Description format: `👉 Try <Tool> (affiliate): useandlike.com/<slug>` (an "A vs B" title gets one per compared tool we have a link for) then the 📩 newsletter line, then an empty line.
  The page also has an "Outro for every new video" box (Kevin, 15 Oct: spoken line at the end of every video; optional
  end-card pictures in `team-links/outro/`, 1920x1080, made from the presenters' tracker pictures) and a "To fix in YouTube Studio" popup for the manager with two tabs: Titles (Kevin, 15 Oct: titles "weirdly
  worded for youtube"; `data/title-fixes.json` from useandlike-ops/analysis/title-fixes.py, whose `check` drops titles
  already changed on YouTube) and Game videos (Kevin, 15 Oct: game videos filed as "Howto & Style" -> category Gaming +
  the game, which links them to the game's page on YouTube; `data/game-category.json` from
  useandlike-ops/analysis/game-category.py, busiest first). Re-run build-editor-lists.py after either; the popup opens
  once a day while some are left, Done ticks stay on the device.
  Some links only go on some of their tool's videos: `LINK_ONLY_IF` in build-editor-lists.py (Skool, Kevin 14 Oct: only where
  viewers would start their own community: create/start/vs/review/pricing/tutorial, not settings videos); the box says why.
  Topics (29 Oct, Kevin: "types in budget ... and get the list of all affiliate offers that fit"): `data/offer-topics.json`
  says what each link is for (shared phrase sets + slug -> topics); the page's search finds links by topic, and a title
  that names none of our tools gets the fitting offers as buttons to pick by hand (deal on the deals page first, then site
  tools, then `worth`). A new link gets its topics there. The box also gives a prompt for a longer AI-written description
  that keeps our lines on top (uploaders had moved the link down as "🔗 Get …"; the page now says the 👉 line is always
  the first line), and a video-plan prompt for the editor (Kevin, 29 Oct: structure ideas for titles with no clear app):
  scenes that solve the viewer's problem first, then at most one of our offers where it really helps (the title's tool,
  else its topic fits, else every site tool), with the spoken affiliate note; none on cancel/refund/"free" titles. Since 29 Oct `make_matcher(tools, read_links(tools))` also finds link-only brands by name (as the box
  does; `NO_AUTO`, `NO_AUTO_FIRST`, `LINK_NOT_ABOUT`), and `lines_for(title, channel)` keeps "only" links to their channel.
- Affiliate links live ONLY in `_redirects` (Cloudflare short links), e.g.
  `/wise  https://wise.prf.hn/click/camref:...  302`. Each tool's `slug` in `TOOLS` points at one,
  and its Visit button goes to `/slug`. The owner also uses these short links in YouTube descriptions,
  so never rename or remove a slug without warning them (old descriptions would break).
- `_redirects` has a generated block (`# >>> yazing-add` ... `# <<< yazing-add`, 13 Oct 2026: 344 Yazing brands that
  fit our channels, Kevin: "every single app or program that would fit"), written by useandlike-ops/analysis/yazing-add.py
  from `data/short-links.json`. Change those links in the JSON and re-run the script, not by hand inside the markers.
  They have no videos yet, so they aren't tools on the page; when one gets videos, it can become a tool (same slug).
  A brand that leaves Yazing (its yazing.com/deals page then opens Yazing's "Top Coupons"; the Studio's deal tracker lists
  it as "Not on Yazing any more" under the Discounts tab's problems): `"source": "Left Yazing"` plus `"paused"` in
  data/short-links.json, re-run yazing-add.py, and put its line in the hand-written `# Left Yazing` block, pointing at the
  brand's own site. The slug stays; paused links are off the team page, the box and the deal tracker (1 Nov 2026: 11 brands).
- Travelpayouts (28 Oct 2026, Kevin's account, YouTube projects): tpx.lt links in the hand-written `# Travelpayouts` block
  of `_redirects` (`"source": "Travelpayouts"` in `data/short-links.json`). /klook, /airhelp and /tiqets moved there from
  Yazing because Travelpayouts pays more; Airalo and Kiwi.com stay on Yazing. A moved entry keeps its `"yazing"` field, so
  yazing-add.py doesn't give the brand a second slug and the Studio's deal tracker keeps reading its Yazing page.
- Involve Asia (30 Oct 2026, Kevin's account; How To Rocket and Guide Glimpse are approved properties, useandlike.com
  is not): invl.me / miniurl.app links in the hand-written `# Involve Asia` block of _redirects (`"source": "Involve Asia"`
  in data/short-links.json), plus the tool /shein above it. /shein (Shein Global, up to 21%, many countries) and
  /aliexpress and /alibaba came from Yazing (US only), /kkday (up to 14%) from Travelpayouts (1-5%); moved entries keep their
  `"yazing"` field and sync_deals.py's YAZING_PAGES, so the deal tracker still reads their Yazing page. Brands that
  review applications get a link per channel; an auto-approved brand's link may go on both channels.
- Direct links (30 Oct 2026, Synthesia on Rewardful, `# Synthesia` block of _redirects): a brand whose rules forbid masked
  or short links gets `"direct": true` in data/short-links.json. Its _redirects line stays (the team page, the new-video
  box and the deal tracker read it), but every 👉 line (team page, box, editor lists, the upload checks) carries the
  brand's own link. Never hand out useandlike.com/<slug> for it, and don't make it a site tool (Visit uses the short link).
- Partnerize (Kevin's account; /wise and /malwarebytes are tools): link-only Partnerize links (EaseUS, 30 Oct) go in the
  hand-written `# Partnerize` block of _redirects (`"source": "Partnerize"`). Adobe applied 30 Oct (partners@, review 1-3 weeks).
- FlexOffers (15 Oct 2026) turned down useandlike.com and Guide Glimpse, then approved the account for How To Rocket
  (Kevin's screenshot, 16 Oct: How To Rocket is the only approved traffic source). Its links go ONLY on How To Rocket videos: link-only
  short links (never a tool or Visit button on the site, never on Guide Glimpse or Logic Protocol) with
  `"source": "FlexOffers", "only": "htr"` in `data/short-links.json`. The team page marks them "How To Rocket only" and
  its new-video box offers them only when the uploader picks How To Rocket; check.js fails on a FlexOffers link without
  that mark, used by a tool, or made for another traffic source (the link's foid starts with the source's ID). A script
  that adds lines to old videos must keep these links to How To Rocket.
- Always 302, never 301 (browsers cache 301s, so updated links would not take effect for repeat visitors).
- Newsletter links (19 Oct 2026): every link in a newsletter issue goes through its own short link in the `_redirects`
  block `# >>> newsletter-links` (`/n1-disney` = issue 1, Disney+ item), so useandlike-ops/analysis/newsletter-clicks.py
  counts clicks per topic (Beehiiv's free plan has no per-link report). `/n0-tracker` is the button in Beehiiv's
  welcome email (29 Oct; issue "0" in issues.json). The sign-up boxes don't show the tracker's address: the link
  comes after confirming (#welcome, the welcome email), so the gift is a reason to confirm. They are not affiliate links for the team:
  build-editor-lists.py and clicks.py skip `/n<number>-` slugs. Never put FlexOffers links in the newsletter (How To
  Rocket only); a tool in an issue links to its tool page (`/tool/<slug>/`), not straight to the affiliate.
- `/join` carries UTM tags (`?utm_source=youtube&utm_medium=video` before `#join`) so Beehiiv can record that a subscriber
  came from YouTube; keep the tags when changing that line (the page itself ignores them).
- The home page's `<head>` has `<meta name="fo-verify" ...>`: FlexOffers' ownership check for useandlike.com
  (14 Oct 2026). Keep it; without it FlexOffers can mark the site as unverified. Use meta tags for such checks:
  Cloudflare redirects `/file.html` to `/file`, so "upload this HTML file" checks fail here.
- Write a "/" before the "?" of a link (`https://repurpose.io/?fpr=1`, not `https://repurpose.io?fpr=1`): Cloudflare
  turns the second into `.../?fpr=1/`, breaking the code (14 Oct). check.js fails on it.

## When the owner sends affiliate links or tool changes in chat
1. Update the matching line in `_redirects`. A new tool needs a line there plus an entry in `TOOLS`
   (and maybe a category in `CATEGORIES`); a link-only short link (not on the page) needs the line plus its name and
   group in `data/short-links.json` (the team's links page reads them).
   - Keep the link exactly as given (tracking parameters included). Slugs: short, lowercase, e.g. `/wise`.
   - If a link's tool is unclear, ask which tool it belongs to rather than guessing.
   - Then `python3 scripts/build-videos.py` for a new or renamed tool (finds its videos, then rebuilds the pages),
     otherwise `node scripts/build-pages.js`.
   - Then `python3 scripts/build-editor-lists.py`, so the team's links page (useandlike.com/team-links/) shows the new link.
   - Then `python3 ../useandlike-ops/studio/tools/sync_deals.py`, so the Studio's deal tracker (Discounts tab) reads the
     new program around the clock (Kevin, 28 Oct: "track all our affiliates ... adding of course the new ones"); a new
     direct program (not Yazing) also needs the page to read in that tool's `SITES`.
2. Run `node scripts/check.js --online` and fix any FAIL. The cloud session's network policy may block
   affiliate hosts ("could not be opened ... TUNNEL" / 403); say the link wasn't checked, not that it's broken. Report WARN lines that matter in plain language
   (e.g. a link that does not open, or links still left as placeholders).
3. Commit with a short message (e.g. "Add Hostinger affiliate link") and push.
4. Tell the owner what changed, which placeholder links remain, and whether it is live yet
   (it is live only once it is on `main`).

## Content rules
- "description", "why" and "details": neutral and factual. No superlatives ("best", "cheapest", "fastest", "#1"...).
  Don't invent features; if unsure, keep the line generic. The check script blocks common superlatives.
- At most one `isPick: true` per category, chosen by the owner (don't pick for them); it is shown first with an "Our pick" label.
- Visit links must keep `rel="sponsored"` (set by the render code). Links open in the same tab by default
  (`OPEN_IN_NEW_TAB = false`; the owner chose this for phone visitors). New tab adds `target="_blank"` + `noopener`.
- No page between the list and the affiliate site: Visit goes /slug -> affiliate link directly (owner's choice).
- Keep the affiliate disclosure in the footer.
- Category pages are `/category/` + the category name in lowercase, `&` → `and`, spaces → `-`
  (e.g. `useandlike.com/category/web-hosting/`); the old `useandlike.com/#web-hosting` links forward there.
  Renaming a category changes both, so warn the owner because old YouTube descriptions would stop opening that category.
  Tool pages use the tool's slug (`/tool/wise/`), another reason never to rename a slug.
- The small pages (About, How we choose tools, How we make money, Work with us) follow the same rules: factual, no
  promises the owner hasn't made, no prices or private numbers on Work with us until the owner sets them.
