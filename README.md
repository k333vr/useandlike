# useandlike.com

A directory of apps and tools we use, with affiliate links: the home page (`index.html`) plus a real page per category
and per tool, made by `node scripts/build-pages.js`. Plain static files: no frameworks, no tracking.

## How to edit the links

Open `index.html`. The **EDIT HERE** block is near the top:

- `CHANNELS`: your YouTube channels (name and @handle). The Videos tab links to them and searches each one for a tool.
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

## Pages per category and per tool

After editing the EDIT HERE block, run `node scripts/build-pages.js`. It writes a page for every category and tool,
the About / How we choose tools / How we make money / Work with us pages (their texts are at the top of the script),
`sitemap.xml` and `robots.txt`. Handy links for YouTube descriptions:

- Category: https://useandlike.com/category/web-hosting/ (the older https://useandlike.com/#web-hosting forwards there)
- Tool: https://useandlike.com/tool/wise/ (the short link https://useandlike.com/wise still goes straight to Wise)
- Videos tab: https://useandlike.com/#videos, or one category: https://useandlike.com/#videos-email

## Cloudflare settings

The site runs as a Cloudflare Worker named `useandlike` that serves the files in this folder,
using the build settings in the Cloudflare dashboard. Pushing to `main` deploys the live site.

## Checking the page

`node scripts/check.js` tests the site in a phone-sized browser (light and dark): data is complete, at most one
"Our pick" per category, the category and tool pages are up to date and work, old # links forward, the back button
works, no superlatives, affiliate links marked as sponsored, videos point at real tools, the sitemap lists only
finished pages, no sideways scrolling.
Add `--online` to also open every real affiliate link. `CLAUDE.md` describes the update routine for Claude.
