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
and where to get them. No daily limit. A mix, not only the big outlets: smaller sites and communities (Reddit) count
when the facts are clear.

**Reddit doesn't open from the cloud** (403; the 2 Nov run skipped its Reddit candidates for that reason). For a Reddit
post about a new app, use the app's own page as the source instead: its App Store or Google Play listing, or its website
(what it does, price, platforms, who makes it). Skip it if that page doesn't open, the app isn't out yet, or it's a
browser extension or side project with no clear use for everyday people. A Reddit-only claim about something else (a
rumor, a bug report) needs an outlet that wrote about it.

**One-liners for the rest** (Kevin, 3 Nov 2026: "lets see how these short items will do", after asking for "all the
stories we filtered there on the day"): every candidate that is real news for our readers but doesn't get a full
story (smaller news, a minor update, a second-tier app, a story with only one or two facts) becomes a one-liner
(`"quick": true`: `head`, `dek` of one or two sentences, `apps`, `sources`), checked in its source like any story.
Only skip what isn't news for everyday app users, can't be confirmed, or is already covered. No limit: on 1-2 Nov the
morning AI marked 50-60 candidates a day as news, and the run wrote 15-16 full stories, so expect 20-40 one-liners a
day. One-liner pages are `noindex` and stay out of the sitemap (thin pages could hold back the full stories' Google
ranking); they show on /news/ under each block of stories and on the front page.

**Rumors, leaks and features in testing** are stories too (Kevin, 1 Nov: "I do also want speculative not approveable
stories we can frame them exactly like that ... more uniqueness is good"): an app's next feature spotted in a beta or its
code, a leaked plan or price, a report that a company is working on something. They get `"rumor": true` and are framed
as exactly that (see the rules). The morning AI marks them `News: rumor`.

Not a story: developer tools, business or enterprise software, crypto and trading, rumors nobody is named for (not even
an outlet or a leaker), rumors about a person's private life, health or crimes, lawsuits, company finance, sports,
celebrities, a tip or opinion piece with no news in it, anything older than about 3 days (unless a date in it is still
ahead, like a change that starts next week).

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
- **Rumors say they're rumors**, everywhere: the headline ("WhatsApp may let you ...", "Instagram is testing ...",
  "Leak: ..."), the dek names who says so ("according to a leak shared by ...", "spotted in the app's code by ...") and
  that the company hasn't confirmed it, and nothing is written as a fact that isn't one. Tag `Rumor`, `Leak` or
  `In testing`. If a later candidate confirms or denies an earlier rumor, update that story (text, `updated`, the new
  source) instead of writing a new one, and drop `rumor` once it's official.
- **Pictures:** none, unless it's one of our own (the newsletter cards in `img/nl/`). Never press photos, screenshots
  or logos from the sources. Without a picture the page shows the app's first letter.

## The fields

| Field | What goes in |
|---|---|
| `slug` | The page address: lowercase words with hyphens, the app plus what changed, at most about 6 words (`reddit-account-for-most-pages`). Never rename one once it's live. |
| `date` | When the news came out (the source's date), `YYYY-MM-DD`. |
| `added`, `checked` | Today: when we wrote it and checked the facts. |
| `topic` | One word: AI, Android, Apple, Google, Social, Messaging, Streaming, Music, Money, Shopping, Travel, Email, Security, Privacy, Cloud, Video, Business ... |
| `tag` | The small label: `New feature`, `New app`, `Update`, `Heads-up`, `Safety`, `Privacy`, `Price change`, `Shutdown`, `Offer`, `Big news`; `Rumor`, `Leak`, `In testing` for rumors; `Quick` for one-liners. |
| `category` | Optional: one of the site's categories (e.g. `Cloud Storage`, `Travel`), when the story fits one and the topic doesn't say it already. It picks the how-to videos shown under the story. |
| `head` | The headline, at most about 70 characters, sentence case, says what changed (`Samsung News shuts down on 21 December`). No question headlines, no clickbait. |
| `dek` | One or two sentences: what happened, for whom, from when. Doesn't repeat the headline's words. |
| `details` | Optional, up to 4 short sentences: the rest of the facts (prices, limits, who announced it, what's still unknown). |
| `where` | Short: who gets it and when (`US, rolling out now in Samsung Wallet`). |
| `means` | "What it means for you": one or two sentences from the reader's side (`If you ...`). |
| `todo` | "What to do": concrete steps the source supports, or a safe general step ("update the app"); "Nothing to do yet" is fine. |
| `rank` | Order within its day (1, 2, 3 ...). Rank 1 only for the day's story that should lead the front page (the newest rank-1 story of the last 3 days leads); at most one rank 1 per day, none on a quiet day. |
| `quick` | `true` for a one-liner (only `head` and `dek`, plus `apps` and `sources`): small news that needs no page of its own. |
| `rumor` | `true` for a rumor, leak or feature in testing: the page shows its tag in amber and a "Not confirmed" note. |
| `apps` | The app names as people write them (`["WhatsApp"]`): they pick our how-to videos about the app. |
| `item` / `items` | The Studio story id it came from / other Studio ids of the same news (other outlets), so the daily run doesn't write it twice. |
| `sources` | `[{"name": "9to5Mac", "url": "https://..."}]`: every outlet you took a fact from, the official source first when there is one. |
| `image`, `thumb`, `video`, `howtos`, `updated` | Optional: our own 2:1 picture and its small version; our news video's YouTube id; video ids for the how-to row; the date of a later correction. |

## The daily run (routine "Use & Like daily news pages")

1. `git pull origin main`. (2 Nov: after a rebuild the cloud machine's `python3` was Python 3.11, which can't load
   Pillow: "cannot import name '_imaging'". Then run every `python3` step below with `/usr/bin/python3`.)
2. `python3 scripts/news-intake.py todo > /tmp/todo.json`: the Studio's candidates from the last 3 days that aren't
   on the site, those the morning AI marked `News: story` first, each with other outlets in `also`.
3. Read `/tmp/todo.json` and the stories already in `data/news/` from the last days. For each candidate decide:
   - **write it** (rules above; open its link and the `also` links you need),
   - **already covered**: the same news is in a story (same app, same change): add the candidate's id to that
     story's `items` (and a source if it adds a fact), or
   - **one-liner** (`"quick": true`) when it's news for our readers but not worth a full story (see "One-liners for
     the rest" above; since 3 Nov this replaces skipping smaller news), or
   - **skip** it (not news for everyday app users, can't confirm the facts, or the link doesn't open and no other
     source has it).
   Merge several candidates about the same news into one story. Give the day's most important story rank 1 when it
   deserves to lead the front page.
4. `python3 scripts/app-icons.py`, on every run, also when no story went up (the picture of every app named in "apps",
   shown as the story's picture when it has none of its own: Kevin's pick from the Studio's Icons tab first, then the
   thumbnail tool's saved logo, then the App Store; it also takes an app's new logo when the app changed it). Since 2 Nov an
   App Store app is only used when its name or maker fits (`trusted()`); a doubtful one leaves the letter, and earlier
   automatic picks that fail the check are taken back by themselves. Read what it picked; a wrong app ("picked
   automatically: check it") is Kevin's to change in the Studio's Icons tab, so mention it in the last line instead of
   editing data/app-icons.json by hand. Short names the App Store lists under a full name ("Copilot" -> "Microsoft
   Copilot") go in `STORE_TERMS` in the script. Then `python3 scripts/partner-offers.py` (every run: the
   offers our partner brands list, from the Studio's deal tracker, for the "More offers from our partners" part of
   /deals/; it leaves out old, seasonal and non-offers by itself). Then `node scripts/story-pictures.js` (every run:
   draws the pictures of new or changed stories in a few seconds into img/stories/: the share picture people see when
   a story is shared, the picture on the story page and the front page, the small one in lists; Kevin, 2 Nov: "that's
   how it should also look on the website"). Then
   `node scripts/build-pages.js`, then `node scripts/check.js` and fix every FAIL (a word on the banned list: reword).
   Write each app in "apps" the way people know it ("WhatsApp", "Google Maps"), one app per entry.
5. Commit only `data/news/`, new app icons (`img/apps/`, `data/app-icons.json`), `data/partner-offers.json`, the story pictures (`img/stories/`, `data/story-pictures.json`) and what the build changed (`news/`, `deals/`,
   `index.html`, `how-tos/`, `sitemap.xml`, the category and tool pages): `git commit -m "News: <n> stories (<date>)"`, then `git push origin main` (main only:
   Cloudflare deploys it in about a minute). Never change `_redirects`, the tools or anything else in this run.
6. Check one new page on useandlike.com after a minute or two (curl it for its headline).
7. Scripts: write one for every new full story of today (see "Scripts for the presenter" below) into
   `/tmp/scripts.json`, then `python3 scripts/news-scripts.py save /tmp/scripts.json` (fix what it reports).
8. End with one line: how many full stories and one-liners went up (headlines of the top 3), how many scripts, how many candidates were
   already covered or skipped. A day without new stories is fine: say so and push nothing.

## Scripts for the presenter

Kevin, 1 Nov 2026: a presenter reads short news videos from a teleprompter, one video per story ("even when its only
30 seconds"), and proofreads each script first with an "alternative script on click". Every full story of the day (not
the one-liners) gets a script; she reads them on scripts.useandlike.com (Studio page,
`useandlike-ops/studio/public/scripts/`): picks a version, may edit it, adds her own take, approves, records (one at a
time or all in one session). Kevin strikes the ones he doesn't want. A script she already worked on is never overwritten.

- **Three versions**, all from the story's checked facts only (nothing that isn't in the story file):
  - `A`, the news straight: 90-160 words (about 40-65 seconds).
  - `B`, the explainer: what happened, why it matters, what to do: 140-230 words (about 60-95 seconds).
  - `C`, short: 45-90 words (20-40 seconds; also fits a Short).
- **Spoken English:** short sentences (most under 15 words), contractions (it's, you'll), no brackets, no
  abbreviations ("for example", not "e.g."), numbers the way people say them ("13 dollars a month", "two terabytes",
  "November 13th"), no web addresses.
- **Start with the news itself** in one plain sentence. No "Hey guys", no "In today's video", no hype, no question
  you don't answer.
- **No spoken call to action** (Kevin, 1 Nov: "a spoken reminder for subscribe and newsletter would be maybe too much
  ... only something visible maybe in the outro"): no "subscribe", no newsletter, no website in the text; the video's
  short end card shows them. End on the last useful sentence (what to do, what's still open), never the same closing
  sentence twice in a day, so the videos don't sound like a template (YouTube doesn't pay for "generic, repetitive or
  template-based" videos). Her own take, read after the text, is the most personal part of each video.
- **`takes`**: 2-3 one-line reactions she can pick from or replace with her own (Kevin: "inserts her newly learned
  opinions or comments on each topic"): clearly opinion, in first person, at most about 15 words, no new facts, nothing
  about a person ("I'd switch this off today.", "Honestly, this is the update I wanted.", "Pins that never expire? Finally.").
  Bold, funny or a bit wild is welcome (Kevin, 1 Nov: "she can give her fancy opinion ... or crazy take fine too but we
  dont twist the facts"): the take is her opinion about the facts, never a different version of them. It never
  claims something the story doesn't say, never makes a rumor sound confirmed, and never mocks people.
- **`points`**: 3-6 key points in speaking order, a few words each (at most 70 characters, not full sentences), for the
  teleprompter's "Key points" mode, where she says the story in her own words instead of reading it (Kevin, 1 Nov: it
  "need[s] to be natural"). The first point is the news, then what changes, who gets it and when, what to do. Example:
  "WhatsApp: catch-up button in groups" / "Shows what you missed since you last looked" / "Android and iPhone, this week" /
  "Find it at the top of a busy group". Rumors: the first point says "Spotted in testing" or "Reportedly".
- **Rumors** stay rumors when spoken: "reportedly", "according to a leak", "spotted in testing", and say once that it
  isn't confirmed.
- **`facts`**: 3-6 short lines she can check against the script: the numbers, dates, places and plans it says.
- **Each script stands alone**: the editor also joins the day's recorded stories into the next day's "If you missed it"
  compilation, so no "as I said", "in my last video" or "next up".
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
  After the lead, put the stories most viewers care about first; between two similar ones, the money topic goes first
  (payments and banking, subscriptions and prices, AI subscriptions, security and VPNs, shopping, travel): those videos
  earn more per view than games or chat apps (Kevin, 1 Nov: "short videos can still have good rev especially if its high
  rpm topics/apps"). If she can't record them all, the top of the list is what gets made.
