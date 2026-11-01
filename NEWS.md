# App news on useandlike.com: how a story is written and the daily run

Kevin, 1 Nov 2026: "basically no limit and also a lot of newcomer apps not only top apps everything thats worth
reporting". Every story is one file, `data/news/<slug>.json`; `node scripts/build-pages.js` turns the files into the
story pages (`/news/<slug>/`), the list (`/news/`), the feed (`/news/feed.xml`) and the front page.

## Who we write for

People who watch our How To Rocket and Guide Glimpse tutorials: everyday app users around the world, mostly on phones,
often because they're stuck or want to save money. Not developers, not investors. Plain words, short sentences.

## What becomes a story

Anything that changes how everyday people use an app or what they pay: new features people can use now, redesigns,
shutdowns, price and plan changes, outages, privacy and safety changes, scams going around, offers with clear terms.
New apps an everyday person could use now, also small and unknown ones, when it's clear what they do, what they cost
and where to get them. No daily limit.

Not a story: developer tools, business or enterprise software, crypto and trading, rumors without a named source,
lawsuits, company finance, sports, celebrities, betas few people can use, a tip or opinion piece with no news in it,
anything older than about 3 days (unless a date in it is still ahead, like a change that starts next week).

## The rules

- **Facts only from the sources.** Open every source you name and use only what it says. If a fact isn't in a source,
  leave it out (no menu paths, prices, countries or dates from memory). If the sources disagree, use the official one
  (the company's blog or support page) or leave the detail out. A Google News link often doesn't open: search for the
  headline and use the outlet's own page instead.
- **Our own words.** Never copy sentences from a source; short facts (names, numbers, dates) are fine.
- **Neutral.** No superlatives or hype ("best", "huge", "game-changer", "must-have", "#1" ...); check.js fails on
  the common ones. Say what happened, for whom, from when. "Free" only for what really costs nothing, with the terms.
- **Exact about who gets it:** country, platform (Android, iPhone, web, Mac, Windows), plan (free, Plus, Pro),
  date, "rolling out" vs "out now". Most stories are US-only or staged: say so.
- **Safety stories** say what to do in plain steps from the source; never link to the scam or the malware.
- **Pictures:** none, unless it's one of our own (the newsletter cards in `img/nl/`). Never press photos, screenshots
  or logos from the sources. Without a picture the page shows the app's first letter.

## The fields

| Field | What goes in |
|---|---|
| `slug` | The page address: lowercase words with hyphens, the app plus what changed, at most about 6 words (`reddit-account-for-most-pages`). Never rename one once it's live. |
| `date` | When the news came out (the source's date), `YYYY-MM-DD`. |
| `added`, `checked` | Today: when we wrote it and checked the facts. |
| `topic` | One word: AI, Android, Apple, Google, Social, Messaging, Streaming, Music, Money, Shopping, Travel, Email, Security, Privacy, Cloud, Video, Business ... |
| `tag` | The small label: `New feature`, `New app`, `Update`, `Heads-up`, `Safety`, `Privacy`, `Price change`, `Shutdown`, `Offer`, `Big news`; `Quick` for one-liners. |
| `category` | Optional: one of the site's categories (e.g. `Cloud Storage`, `Travel`), when the story fits one and the topic doesn't say it already. It picks the how-to videos shown under the story. |
| `head` | The headline, at most about 70 characters, sentence case, says what changed (`Samsung News shuts down on 21 December`). No question headlines, no clickbait. |
| `dek` | One or two sentences: what happened, for whom, from when. Doesn't repeat the headline's words. |
| `details` | Optional, up to 4 short sentences: the rest of the facts (prices, limits, who announced it, what's still unknown). |
| `where` | Short: who gets it and when (`US, rolling out now in Samsung Wallet`). |
| `means` | "What it means for you": one or two sentences from the reader's side (`If you ...`). |
| `todo` | "What to do": concrete steps the source supports, or a safe general step ("update the app"); "Nothing to do yet" is fine. |
| `rank` | Order within its day (1, 2, 3 ...). Rank 1 only for the day's story that should lead the front page (the newest rank-1 story of the last 3 days leads); at most one rank 1 per day, none on a quiet day. |
| `quick` | `true` for a one-liner (only `head` and `dek`, plus `apps` and `sources`): small news that needs no page of its own. |
| `apps` | The app names as people write them (`["WhatsApp"]`): they pick our how-to videos about the app. |
| `item` / `items` | The Studio story id it came from / other Studio ids of the same news (other outlets), so the daily run doesn't write it twice. |
| `sources` | `[{"name": "9to5Mac", "url": "https://..."}]`: every outlet you took a fact from, the official source first when there is one. |
| `image`, `thumb`, `video`, `howtos`, `updated` | Optional: our own 2:1 picture and its small version; our news video's YouTube id; video ids for the how-to row; the date of a later correction. |

## The daily run (routine "Use & Like daily news pages")

1. `git pull origin main`.
2. `python3 scripts/news-intake.py todo > /tmp/todo.json`: the Studio's candidates from the last 3 days that aren't
   on the site, those the morning AI marked `News: story` first, each with other outlets in `also`.
3. Read `/tmp/todo.json` and the stories already in `data/news/` from the last days. For each candidate decide:
   - **write it** (rules above; open its link and the `also` links you need),
   - **already covered**: the same news is in a story (same app, same change): add the candidate's id to that
     story's `items` (and a source if it adds a fact), or
   - **skip** it (not a story, can't confirm the facts, or the link doesn't open and no other source has it).
   Merge several candidates about the same news into one story. Give the day's most important story rank 1 when it
   deserves to lead the front page.
4. `node scripts/build-pages.js`, then `node scripts/check.js` and fix every FAIL (a word on the banned list: reword).
5. Commit only `data/news/` and what the build changed (`news/`, `index.html`, `how-tos/`, `sitemap.xml`, the
   category and tool pages): `git commit -m "News: <n> stories (<date>)"`, then `git push origin main` (main only:
   Cloudflare deploys it in about a minute). Never change `_redirects`, the tools or anything else in this run.
6. Check one new page on useandlike.com after a minute or two (curl it for its headline).
7. Scripts: write one for every new full story of today (see "Scripts for the presenter" below) into
   `/tmp/scripts.json`, then `python3 scripts/news-scripts.py save /tmp/scripts.json` (fix what it reports).
8. End with one line: how many stories went up (headlines of the top 3), how many scripts, how many candidates were
   already covered or skipped. A day without new stories is fine: say so and push nothing.

## Scripts for the presenter

Kevin, 1 Nov 2026: a presenter reads 1-3 minute news videos from a teleprompter, and proofreads each script first with
an "alternative script on click". Every full story of the day (not the one-liners) gets a script; she reads them on
scripts.useandlike.com (Studio page, `useandlike-ops/studio/public/scripts/`): picks a version, may edit it,
approves, records. Kevin strikes the ones he doesn't want. A script she already worked on is never overwritten.

- **Three versions**, all from the story's checked facts only (nothing that isn't in the story file):
  - `A`, the news straight: 120-200 words (about 50-80 seconds).
  - `B`, the explainer: what happened, why it matters, what to do: 160-280 words (about 65-110 seconds).
  - `C`, short: 55-110 words (25-45 seconds; also fits a Short).
- **Spoken English:** short sentences (most under 15 words), contractions (it's, you'll), no brackets, no
  abbreviations ("for example", not "e.g."), numbers the way people say them ("13 dollars a month", "two terabytes",
  "November 13th"), no web addresses except "useandlike dot com".
- **Start with the news itself** in one plain sentence. No "Hey guys", no "In today's video", no hype, no question
  you don't answer.
- **Vary the endings:** the three versions of a script end differently, and a day's scripts don't use the same closing
  sentence in the same version, so the videos don't sound like a template (YouTube doesn't pay for "repetitive or template-based" videos). For example: "The details are on
  useandlike dot com." / "We put the steps on useandlike dot com." / "That's the short version; the full story is on
  useandlike dot com." / "If you want news like this every morning, our free newsletter is on useandlike dot com."
  The newsletter in at most one version per script.
- **`facts`**: 3-6 short lines she can check against the script: the numbers, dates, places and plans it says.
- **For the uploader:** `title` (about 60 characters at most, app name first, plain words, no clickbait or capitals)
  and `description`:

  ```
  <one sentence: what happened>
  Full story: https://useandlike.com/news/<slug>/
  📩 Free 30-second app newsletter: https://useandlike.com/join
  Source: <the outlets>
  ```
- Examples: the six scripts of 1 Nov 2026 (`python3 scripts/news-scripts.py list --day 2026-11-01`).
- **`code`** = "N" + month and day of today + "-" + `rank` in two digits (`N1102-01`); `day` = today; `rank` = the
  order she should record them in (the lead story first). Also `slug`, `item`, `head` and `sources` from the story.
