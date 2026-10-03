# useandlike.com

A one-page list of apps and tools we use, with affiliate links. Plain static files: no build step, no frameworks, no tracking.

## How to edit the links

Open `index.html`. The **EDIT HERE** block is near the top:

- `CHANNEL_SEARCH_URL`: where "Watch our video" buttons go. The tool name is added to the end.
  To search only your channel, use `https://www.youtube.com/@YOURCHANNEL/search?query=`.
- `VISIBLE_COUNT`: how many tools show before the "Show all" button.
- `CATEGORIES`: the category list, in order.
- `TOOLS`: one entry per tool. Replace each `url` (`https://example.com/...`) with your affiliate link.
  Set `isPick: true` on one tool per category to show the "Our pick" label.

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
