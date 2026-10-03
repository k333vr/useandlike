# useandlike.com

A one-page list of apps and tools we use, with affiliate links. Plain static files: no build step, no frameworks, no tracking.

## How to edit the links

Open `index.html`. The **EDIT HERE** block is near the top:

- `CHANNEL_SEARCH_URL`: where "Watch our video" buttons go. The tool name is added to the end.
  To search only your channel, use `https://www.youtube.com/@YOURCHANNEL/search?query=`.
- `VISIBLE_COUNT`: how many tools show before the "Show all" button.
- `CATEGORIES`: the category list, in order.
- `TOOLS`: one entry per tool. `slug` is its short link (`slug: "hostinger"` -> useandlike.com/hostinger).
  Set `isPick: true` on one tool per category to show the "Our pick" label.

## Affiliate links (short links)

The real affiliate links are in `_redirects`, one per line:

```
/wise  https://wise.prf.hn/click/camref:1110l4ToH  302
```

So useandlike.com/wise sends visitors straight to the affiliate link. Use these short links in YouTube
descriptions; when an affiliate link changes, update that one line and every old video still works.
Short links only work on the live site (Cloudflare), not when opening index.html on your computer.

Save, commit, and push to `main`. Cloudflare Pages updates the site within a minute or two.

## Linking straight to a category

Each category has its own link, which is handy in YouTube descriptions:

- https://useandlike.com/#vpn-and-privacy
- https://useandlike.com/#email
- https://useandlike.com/#cloud-storage
- https://useandlike.com/#web-hosting
- https://useandlike.com/#online-stores-and-funnels

## Cloudflare Pages settings

- Framework preset: **None**
- Build command: *(leave empty)*
- Build output directory: `/`
- Production branch: `main`

## Checking the page

`node scripts/check.js` tests the page in a phone-sized browser (light and dark): data is complete, one "Our pick"
per category, no superlatives, affiliate links marked as sponsored, no sideways scrolling.
Add `--online` to also open every real affiliate link. `CLAUDE.md` describes the update routine for Claude.
