# useandlike.com — notes for Claude

The owner is a beginner. Explain things in plain language and do as much as possible yourself.

## The site
- One static page: `index.html` (CSS and JS inline). No frameworks, no build step, no tracking scripts, no external requests.
- Hosted on Cloudflare Pages from the `main` branch. Pushing to `main` deploys to useandlike.com.
- All editable content is in the `EDIT HERE` block at the top of `index.html`:
  `CHANNEL_SEARCH_URL`, `VISIBLE_COUNT`, `CATEGORIES`, `TOOLS`.
- Affiliate links live ONLY in `_redirects` (Cloudflare Pages short links), e.g.
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
- "Why we use it" lines: neutral and factual. No superlatives ("best", "cheapest", "fastest", "#1"...).
  Don't invent features; if unsure, keep the line generic. The check script blocks common superlatives.
- Exactly one `isPick: true` per category that has tools; it is shown first with an "Our pick" label.
- Visit links must keep `rel="sponsored noopener"` and `target="_blank"` (set by the render code).
- Keep the affiliate disclosure in the footer.
- Category links are `#` + the category name in lowercase, `&` → `and`, spaces → `-`
  (e.g. `useandlike.com/#web-hosting`). Renaming a category changes its link, so warn the owner
  because old YouTube descriptions would stop opening that category.
