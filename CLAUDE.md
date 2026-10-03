# useandlike.com — notes for Claude

The owner is a beginner. Explain things in plain language and do as much as possible yourself.

## The site
- One static page: `index.html` (CSS and JS inline). No frameworks, no build step, no tracking scripts, no external requests.
- Hosted on Cloudflare as a Worker named `useandlike` with static assets (Workers Builds, connected to GitHub).
  Pushing to `main` deploys to useandlike.com. Build results show as the "Workers Builds: useandlike"
  check on each commit (`gh api repos/k333vr/useandlike/commits/<sha>/check-runs`).
  Push changes to `main` ONLY. Never push the same commit to another branch: Cloudflare then builds it once as
  a branch preview (`npx wrangler preview`, which hangs at "Initializing" and times out) and skips the `main`
  build, so the site does not update (this happened on 3 Oct 2026 until main-only pushes).
  Do NOT add a `wrangler.jsonc`: Cloudflare's dashboard settings build this repo without one, and adding
  one made production builds fail (commits 274c3d1, de405a4). Re-add only after seeing the build log.
  Test locally: `CLOUDFLARE_CF_FETCH_ENABLED=false npx wrangler dev --assets .` (serves `_redirects` too).
- All editable content is in the `EDIT HERE` block at the top of `index.html`:
  `CHANNELS`, `NEWSLETTER`, `OPEN_IN_NEW_TAB`, `VISIBLE_COUNT`, `CATEGORIES`, `TOOLS`, `VIDEOS`.
- `NEWSLETTER.ready` shows a signup box (home + category pages) linking to `/newsletter`; that line must exist
  in `_redirects` first (the check script enforces it).
- Layout (owner's choice: clean, Craigslist-style, no search): the home page lists every category with its
  first `VISIBLE_COUNT` tool names as direct affiliate links, plus "All N ›". A category heading opens its
  category page (`#web-hosting`): each tool with `description`, optional `why`/`details`, "Our pick" and a
  Visit button, then a "Watch our videos about …" link. The back button returns to the same spot.
- Tool fields: `name`, `category`, `description`, `slug` (short link), `isPick`; optional `why`, `details`.
- `VIDEOS` feeds the Videos tab: `{ title, url, channel, category, tool? }` (url = youtube.com/watch?v=<11-char id>).
  Each video needs a thumbnail at `thumbs/<id>.jpg` (320x180, from https://i.ytimg.com/vi/<id>/mqdefault.jpg),
  so the site makes no requests to YouTube. The Videos tab shows category buttons (side list on wide screens)
  and a card grid; tools without videos get "Search on:" links per channel. `#videos` = all, `#videos-email` = one category.
  Leave out video titles that undercut the affiliate offer ("premium for free", "license key", "trial reset", "free alternative").
- Affiliate links live ONLY in `_redirects` (Cloudflare short links), e.g.
  `/wise  https://wise.prf.hn/click/camref:...  302`. Each tool's `slug` in `TOOLS` points at one,
  and its Visit button goes to `/slug`. The owner also uses these short links in YouTube descriptions,
  so never rename or remove a slug without warning them (old descriptions would break).
- Always 302, never 301 (browsers cache 301s, so updated links would not take effect for repeat visitors).

## When the owner sends affiliate links or tool changes in chat
1. Update the matching line in `_redirects`. A new tool needs a line there plus an entry in `TOOLS`
   (and maybe a category in `CATEGORIES`); a link-only short link (not on the page) needs just the line.
   - Keep the link exactly as given (tracking parameters included). Slugs: short, lowercase, e.g. `/wise`.
   - If a link's tool is unclear, ask which tool it belongs to rather than guessing.
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
- Category links are `#` + the category name in lowercase, `&` → `and`, spaces → `-`
  (e.g. `useandlike.com/#web-hosting`). Renaming a category changes its link, so warn the owner
  because old YouTube descriptions would stop opening that category.
