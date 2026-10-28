# useandlike.com — notes for Claude

The owner is a beginner. Explain things in plain language and do as much as possible yourself.

## The site
- `index.html` (CSS and JS inline): the home page, the Videos tab and the small # pages (join, welcome, privacy, tracker).
  Plus real pages made by `node scripts/build-pages.js` from the EDIT HERE block and videos.js (since 11 Oct 2026):
  `category/<name>/`, `tool/<slug>/`, `about/`, `how-we-choose/`, `how-we-make-money/`, `work-with-us/`, `sitemap.xml`,
  `robots.txt`; plus the hidden `team-links/` page from `scripts/build-editor-lists.py`. The generated files are committed (Cloudflare has no build step). It also refreshes two marked blocks in
  index.html (`build-pages:ld` structured data, `build-pages:home` the category list as plain HTML for crawlers that
  don't run JavaScript). No frameworks, no tracking scripts, no external requests (except Beehiiv's signup form, see NEWSLETTER).
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
- Layout (owner's choice: clean, Craigslist-style, no search): the home page lists every category with its
  first `VISIBLE_COUNT` tool names as direct affiliate links, plus "All N ›". A category heading opens its
  category page (`/category/web-hosting/`): each tool with `description`, optional `why`/`details`, "Our pick", a
  Visit button and a link to its tool page, then our videos about the category. A tool page (`/tool/wise/`): what it
  does, Visit button, all our videos about it ("Show all" after 24), the category's other tools. Old links
  (`useandlike.com/#web-hosting`, `#about`) forward to the real pages. Tool pages with fewer than 3 videos and no
  `why`/`details` (and thin categories) are `noindex` and stay out of the sitemap until they have more.
- Tool fields: `name`, `category`, `description`, `slug` (short link), `isPick`; optional `why`, `details`.
- Channel videos: `videos.js` (generated, ~2,250 videos about our tools) is loaded only when the Videos tab opens;
  the category and tool pages list the same videos as plain HTML.
  Refresh: `scripts/fetch-videos.sh` (yt-dlp, all videos of the 3 channels -> `data/channel-videos.tsv`), then
  `python3 scripts/build-videos.py` (matches titles to TOOLS, drops Shorts and titles like cancel/refund/delete account/free alternative
  and other products with the same name (NOT_ABOUT, e.g. Nolo VR, WiseCleaner), downloads missing thumbnails, rebuilds the pages). Re-run build-videos.py after adding or renaming a tool. Videos tab pages 24 at a time.
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
- Affiliate links live ONLY in `_redirects` (Cloudflare short links), e.g.
  `/wise  https://wise.prf.hn/click/camref:...  302`. Each tool's `slug` in `TOOLS` points at one,
  and its Visit button goes to `/slug`. The owner also uses these short links in YouTube descriptions,
  so never rename or remove a slug without warning them (old descriptions would break).
- `_redirects` has a generated block (`# >>> yazing-add` ... `# <<< yazing-add`, 13 Oct 2026: 344 Yazing brands that
  fit our channels, Kevin: "every single app or program that would fit"), written by useandlike-ops/analysis/yazing-add.py
  from `data/short-links.json`. Change those links in the JSON and re-run the script, not by hand inside the markers.
  They have no videos yet, so they aren't tools on the page; when one gets videos, it can become a tool (same slug).
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
  counts clicks per topic (Beehiiv's free plan has no per-link report). They are not affiliate links for the team:
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
