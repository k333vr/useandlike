# useandlike.com

A one-page list of apps and tools we use, with affiliate links. Plain static files: no build step, no frameworks, no tracking.

## How to edit the links

Open `index.html`. The **EDIT HERE** block is near the top:

- `CHANNEL_SEARCH_URL`: where "Watch our video" buttons go. The tool name is added to the end.
  To search only your channel, use `https://www.youtube.com/@YOURCHANNEL/search?query=`.
- `VISIBLE_COUNT`: how many tool names each category shows on the home page before "All N ›".
- `CATEGORIES`: the category list, in order.
- `TOOLS`: one entry per tool: `description` (short line on the category page), optional `why` and `details`,
  and `slug`, its short link (`slug: "hostinger"` -> useandlike.com/hostinger).
- `VIDEOS`: your videos for the Videos tab (`title`, `url`, `category`, and optionally the `tool` name).
  Set `isPick: true` on at most one tool per category to show the "Our pick" label.

## Affiliate links (short links)

The real affiliate links are in `_redirects`, one per line:

```
/wise  https://wise.prf.hn/click/camref:1110l4ToH  302
```

So useandlike.com/wise sends visitors straight to the affiliate link. Use these short links in YouTube
descriptions; when an affiliate link changes, update that one line and every old video still works.
Short links only work on the live site (Cloudflare), not when opening index.html on your computer.

Save, commit, and push to `main`. Cloudflare updates the site within a minute or two.

## Linking straight to a category

Each category has its own link, which is handy in YouTube descriptions:

- https://useandlike.com/#vpn-and-privacy
- https://useandlike.com/#email
- https://useandlike.com/#cloud-storage
- https://useandlike.com/#web-hosting
- https://useandlike.com/#online-stores-and-funnels
- Videos tab: https://useandlike.com/#videos, or one category: https://useandlike.com/#videos-email

## Cloudflare settings

The site runs as a Cloudflare Worker named `useandlike` that serves the files in this folder.
`wrangler.jsonc` holds its settings, and `.assetsignore` lists files that are not published
(scripts, these notes, config). Pushing to `main` deploys the live site.

## Checking the page

`node scripts/check.js` tests the page in a phone-sized browser (light and dark): data is complete, at most one
"Our pick" per category, every category page and the back button work, no superlatives, affiliate links marked as sponsored, videos point at real tools, no sideways scrolling.
Add `--online` to also open every real affiliate link. `CLAUDE.md` describes the update routine for Claude.
