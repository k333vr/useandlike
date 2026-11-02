#!/usr/bin/env node
// Builds the real pages of useandlike.com, so search engines and AI assistants find a page per category and per tool
// (the home page and the Videos tab stay as they are). Everything comes from the EDIT HERE block of index.html,
// videos.js and the texts below:
//   category/<category>/index.html   the category's tools with Visit buttons, and our most viewed videos about them
//   tool/<slug>/index.html           what the tool does, Visit button, all our videos about it, the other tools
//   about/ how-we-choose/ how-we-make-money/ work-with-us/   (texts in PAGES below)
//   deals/                           running deals at brands we link to (data/deals.json, icons in img/deals/<slug>.webp)
//   sitemap.xml, robots.txt, and in index.html the blocks between the "build-pages" markers
//   (the site's structured data, and the category list as plain HTML for crawlers that don't run JavaScript).
// Pages with little of their own yet (fewer than 3 videos and no "why"/"details") get "noindex" and stay out of the
// sitemap until they have more.
//
// Run after changing the EDIT HERE block, videos.js or the texts below:   node scripts/build-pages.js
// node scripts/build-pages.js --check  only reports out-of-date files (scripts/check.js runs it).
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const SITE = "https://useandlike.com";
const CHECK = process.argv.includes("--check");

/* =====================================================================
   EDIT HERE: the small pages. Plain text; [label](link) makes a link.
   Neutral and factual, like the rest of the site (no "best", no claims we can't show).
   ===================================================================== */
const CONTACT = "HTRocket@proton.me";            // readers: questions, corrections
const BUSINESS = "partners@useandlike.com";       // brands: goes straight into the studio's Offers desk (since 12 Oct)
const PAGES = [
  {
    path: "about/",
    title: "About Use & Like",
    description: "Who is behind Use & Like: the team of the YouTube channels How To Rocket, Guide Glimpse and Logic Protocol.",
    lead: "Use & Like is a directory of apps and tools, put together by the team behind the YouTube channels How To Rocket, Guide Glimpse and Logic Protocol.",
    paragraphs: [
      "We make tutorials for many of these tools: more than 9,000 videos so far, mostly about everyday apps. This site collects the tools in one place, sorted by category, with our videos about each one, so you can see how a tool works before you sign up.",
      "We also make a free [Subscription Tracker](https://subscriptionchef.app/) and a free [app newsletter](/#join).",
      "Contact: [" + CONTACT + "](mailto:" + CONTACT + ")",
      "More: [How we choose tools](/how-we-choose/) · [How we make money](/how-we-make-money/) · [Work with us](/work-with-us/) · [Privacy](/#privacy)"
    ],
    channels: true
  },
  {
    path: "how-we-choose/",
    title: "How we choose and describe tools",
    description: "How the tools on Use & Like are chosen, described and marked, and what affiliate links mean for you.",
    lead: "What you can expect from the tool lists on this site.",
    bullets: [
      "What's listed: hand-picked apps and tools, sorted by category. Most of them have tutorials on our channels.",
      "Descriptions: one short, factual line about what the tool does. No star ratings and no superlatives.",
      "\"Our pick\": at most one per category, the tool we would try first. We choose it ourselves.",
      "Videos: each tool page lists our tutorials about the tool.",
      "Affiliate links: many tools here have one. If you sign up through it, we may earn a commission. You don't pay more.",
      "Prices and features change: check the tool's own site for the current details before you buy."
    ],
    paragraphs: [
      "Spotted something outdated or wrong? Email us: [" + CONTACT + "](mailto:" + CONTACT + ")"
    ]
  },
  {
    path: "how-we-make-money/",
    title: "How we make money",
    description: "Use & Like is free. How we pay for it: affiliate commissions, YouTube ads and labeled sponsorships.",
    lead: "Use & Like is free to use. This is how we pay for it:",
    bullets: [
      "Affiliate commissions: when you sign up for a tool through a link on this site, in our newsletter or in our video descriptions, the company may pay us a commission. You don't pay more.",
      "YouTube ads: YouTube pays us a share of the ads shown on our videos.",
      "Sponsorships: when a company pays us to make or mention a video about its product, we say so in the video and in its description.",
      "The newsletter is free. When it includes affiliate links or a sponsored section, we label them."
    ],
    paragraphs: [
      "Descriptions on this site are short and factual, and written by us. Our free [Subscription Tracker](https://subscriptionchef.app/) needs no sign-up, and your list stays on your device.",
      "Questions: [" + CONTACT + "](mailto:" + CONTACT + ")"
    ]
  },
  {
    path: "work-with-us/",
    title: "Work with us",
    description: "For app makers and brands: tutorials, mentions and newsletter spots on How To Rocket, Guide Glimpse and our app newsletter.",
    lead: "For app makers and brands: reach people while they learn to use apps like yours.",
    paragraphs: [
      "Who watches: everyday app users around the world, mostly on phones, often in the middle of a task: setting up an app, fixing a problem, paying, or trying to save money.",
      "Our channels: How To Rocket and Guide Glimpse (app and AI tutorials) and Logic Protocol, with more than 9,000 videos so far."
    ],
    h2: "What we can do",
    bullets: [
      "A tutorial about your app on one of our channels.",
      "A short mention of your app in one of our tutorials.",
      "Your link in the descriptions and pinned comments of our existing videos about your app.",
      "A mention in our app newsletter."
    ],
    after: [
      "How it works: email us your app, who you want to reach and your timing. We reply with options, our numbers for your app and prices.",
      "Our rules: sponsored content is labeled, and we only show what a tutorial can honestly show. We don't work with gambling, adult content, get-rich schemes or cracked apps.",
      "Email: [" + BUSINESS + "](mailto:" + BUSINESS + ")"
    ],
    channels: true
  }
];
/* ===================== END OF EDIT BLOCK ===================== */

const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
// Escaped text with [label](link) turned into links.
const rich = s => esc(s).replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, label, href) => `<a href="${href}">${label}</a>`);
const slugOf = s => s.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const plural = (n, word) => n + " " + word + (n === 1 ? "" : "s");
// "Web hosting" -> "web hosting", but "VPN service" stays as it is; no full stop at the end.
const sentence = s => (/^[A-Z][a-z]/.test(s) ? s[0].toLowerCase() + s.slice(1) : s).replace(/\.$/, "");
const ytId = url => (String(url).match(/[?&]v=([\w-]{11})/) || [])[1];
const ld = obj => `<script type="application/ld+json">${JSON.stringify(obj).replace(/</g, "\\u003c")}</script>`;

// ---- Read the site ----
const indexPath = path.join(ROOT, "index.html");
const indexHtml = fs.readFileSync(indexPath, "utf8");
const editAt = indexHtml.indexOf("EDIT HERE");
const editCode = indexHtml.slice(indexHtml.lastIndexOf("<script>", editAt) + 8, indexHtml.indexOf("</script>", editAt));
const { CHANNELS, NEWSLETTER, OPEN_IN_NEW_TAB, VISIBLE_COUNT, CATEGORIES, TOOLS, VIDEOS } = vm.runInNewContext(
  editCode + "\n;({ CHANNELS, NEWSLETTER, OPEN_IN_NEW_TAB, VISIBLE_COUNT, CATEGORIES, TOOLS, VIDEOS })", {});
const STYLE = indexHtml.match(/<style>([\s\S]*?)<\/style>/)[1];
const ICON = indexHtml.match(/<link rel="icon"[^>]*>/)[0];
const HEADER = indexHtml.match(/<header>[\s\S]*?<\/header>/)[0];
const FOOTER = indexHtml.match(/<footer>[\s\S]*?<\/footer>/)[0];

const W = {};
vm.runInNewContext(fs.readFileSync(path.join(ROOT, "videos.js"), "utf8"), { window: W });
const DEALS = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "deals.json"), "utf8")).deals;
// Offers our partner brands list on our partner network (scripts/partner-offers.py, refreshed by the daily run; Kevin,
// 1 Nov: "only 7 deals listed ... when we have like 1000s of partners"). Shown under the hand-checked deals, labelled.
const PARTNER = (() => { try { return JSON.parse(fs.readFileSync(path.join(ROOT, "data", "partner-offers.json"), "utf8")); } catch (_) { return { offers: [] }; } })();
const OFFERS = PARTNER.offers || [];
// App icons for the news (scripts/app-icons.py; Kevin, 1 Nov: the site "looks strange just with the letters").
const APP_ICONS = (() => { try { return JSON.parse(fs.readFileSync(path.join(ROOT, "data", "app-icons.json"), "utf8")); } catch (_) { return {}; } })();
// Story pictures from scripts/story-pictures.js (Kevin, 2 Nov 2026: "that's how it should also look on the website"):
// img/stories/<slug>.jpg (share picture, og:image), -art.jpg (story page and front page lead), -thumb.jpg (lists).
const STORY_PICS = (() => { try { return JSON.parse(fs.readFileSync(path.join(ROOT, "data", "story-pictures.json"), "utf8")).stories || {}; } catch (_) { return {}; } })();
const storyPic = (s, kind) => STORY_PICS[s.slug] && fs.existsSync(path.join(ROOT, "img", "stories", s.slug + kind + ".jpg"))
  ? `/img/stories/${s.slug}${kind}.jpg?v=${STORY_PICS[s.slug]}` : null;
const LEAD_PICS = (() => { try { return JSON.parse(fs.readFileSync(path.join(ROOT, "data", "story-pictures.json"), "utf8")).leads || {}; } catch (_) { return {}; } })();
// The front page's top-story picture (Kevin, 2 Nov: options 1, 2, 4, 5 and 7, "we can switch between those and track
// traffic a b test it later"). LEAD_STYLE "" = a different one for each day's top story, in this order; one number
// keeps that style.
// 1 the blue box with the logo (-art), 2 a band with the logo, app name and tag (-lead2), 4 a presenter beside the logo
// (-lead4), 5 the share picture (tag + headline), 7 "Today in apps" (-lead7). scripts/story-pictures.js draws 2, 4 and 7
// for stories with rank 1; a style the story has no picture for is skipped.
const LEAD_STYLE = "";
const LEAD_STYLES = [["1", "-art", 1200, 600], ["2", "-lead2", 1200, 400], ["4", "-lead4", 1200, 600], ["5", "", 1200, 630], ["7", "-lead7", 1200, 400]];
function leadPicture(s) {
  if (s.image) return { src: s.image, w: 1200, h: 600, style: "own" };
  // by the story's date, not the clock, so a rebuild on another day gives the same page (check.js compares them)
  const day = Math.floor(Date.parse(s.date + "T00:00:00Z") / 864e5) % LEAD_STYLES.length;
  const order = LEAD_STYLE ? LEAD_STYLES.filter(x => x[0] === LEAD_STYLE).concat(LEAD_STYLES)
    : LEAD_STYLES.slice(day).concat(LEAD_STYLES.slice(0, day));
  for (const [n, kind, w, h] of order) {
    const src = /^-lead/.test(kind)
      ? (LEAD_PICS[s.slug] && fs.existsSync(path.join(ROOT, "img", "stories", s.slug + kind + ".jpg")) ? `/img/stories/${s.slug}${kind}.jpg?v=${LEAD_PICS[s.slug]}` : null)
      : storyPic(s, kind);
    if (src) return { src, w, h, style: n };
  }
  return null;
}
const DEFAULT_SHARE = fs.existsSync(path.join(ROOT, "img", "share", "default.jpg")) ? "/img/share/default.jpg" : null;

// Our pick first, then the order of TOOLS (as on the home page).
const toolsIn = cat => TOOLS.filter(t => t.category === cat).sort((a, b) => (b.isPick ? 1 : 0) - (a.isPick ? 1 : 0));
const toolByName = new Map(TOOLS.map(t => [t.name, t]));
const hasThumb = id => fs.existsSync(path.join(ROOT, "thumbs", id + ".jpg"));

// Videos per tool and per category: the hand-picked VIDEOS first, then the channel videos (most viewed first).
const toolVideos = new Map(TOOLS.map(t => [t.name, []]));
const catVideos = new Map(CATEGORIES.map(c => [c, []]));
const seenTool = new Set(), seenCat = new Set();
function addVideo(v) {
  const id = ytId(v.url);
  if (!id) return;
  const item = { id, title: v.title, channel: v.channel, tool: v.tool };
  if (v.tool && toolVideos.has(v.tool) && !seenTool.has(v.tool + "|" + id)) {
    seenTool.add(v.tool + "|" + id);
    toolVideos.get(v.tool).push(item);
  }
  if (catVideos.has(v.category) && !seenCat.has(v.category + "|" + id)) {
    seenCat.add(v.category + "|" + id);
    catVideos.get(v.category).push(item);
  }
}
VIDEOS.forEach(addVideo);
(W.CHANNEL_VIDEOS || []).forEach(r => {
  const t = toolByName.get(W.CHANNEL_VIDEO_TOOLS[r[3]]);
  if (t) addVideo({ url: "https://www.youtube.com/watch?v=" + r[0], title: r[1], channel: W.CHANNEL_VIDEO_CHANNELS[r[2]],
                    category: t.category, tool: t.name });
});

const toolPath = t => "tool/" + t.slug + "/";
const catPath = c => "category/" + slugOf(c) + "/";
const toolIndexed = t => toolVideos.get(t.name).length >= 3 || !!(t.why || t.details);
const catIndexed = c => toolsIn(c).length >= 3 || catVideos.get(c).length >= 6;

// ---- Shared pieces ----
const newTab = OPEN_IN_NEW_TAB ? ' target="_blank" rel="noopener"' : "";
const sponsored = `rel="sponsored${OPEN_IN_NEW_TAB ? " noopener" : ""}"${OPEN_IN_NEW_TAB ? ' target="_blank"' : ""}`;
const PLAY = '<svg class="play" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 1l7 4-7 4z" fill="currentColor"/></svg>';
const channelUrl = c => "https://www.youtube.com/" + c.handle;
const channelLinks = urlFor => '<span class="channels">' +
  CHANNELS.map(c => `<a href="${esc(urlFor(c))}"${newTab}>${esc(c.name)}</a>`).join(" · ") + "</span>";

function joinForm(withPerk) {
  const perk = withPerk ? `<p class="perk"><b class="perk-title">${esc(NEWSLETTER.perkTitle)}</b><span class="perk-gift">${esc(NEWSLETTER.perkGift)}</span></p>` : "";
  // Under the field (not in the header): a confirmation email follows, and Beehiiv's own page as a backup (as on index.html).
  const note = withPerk ? "" : '<p class="bh-note">Next: we email you a link. Open your email app and tap Confirm to finish ' +
    '(check Promotions or Spam too). Field not showing? <a href="/newsletter">Sign up here</a>.</p>';
  // The button after the slot shows only if Beehiiv's field is still missing after 5 seconds (CSS + SCRIPT below).
  const fallback = '<p class="bh-fallback"><a href="/newsletter">Open the sign-up page ›</a></p>';
  if (NEWSLETTER.beehiivForm) return `<div class="join-form">${perk}<div class="bh-slot"></div>${fallback}${note}</div>`;
  return `<div class="join-form">${perk}<form action="/newsletter" method="get"><div class="jrow">` +
    `<input type="email" name="email" required placeholder="Your email" autocomplete="email" aria-label="Your email">` +
    `<button type="submit">${esc(NEWSLETTER.button)}</button></div></form></div>`;
}
const newsletterBox = () => !NEWSLETTER.ready ? "" : `<section class="newsletter"><div class="nl-text"><h2>${esc(NEWSLETTER.title)}</h2>` +
  `<p>${esc(NEWSLETTER.text)}</p><p class="nl-perk"><span class="perk-gift">${esc(NEWSLETTER.perkGift)}</span></p></div>` +
  joinForm(false) + '<button type="button" class="nl-hide">Already subscribed? Hide this</button></section>';

function header(current) {
  let h = HEADER.replace(/href="#"/g, 'href="/"').replace(/href="#videos"/g, 'href="/#videos"')
    .replace('<div class="ctas" id="header-join"></div>', `<div class="ctas" id="header-join">${NEWSLETTER.ready ? joinForm(true) : ""}</div>`);
  for (const id of ["news", "howtos", "deals"]) if (current === id) h = h.replace(`id="nav-${id}"`, `id="nav-${id}" aria-current="page"`);
  return h;
}
const footer = () => FOOTER.replace('<p id="foot-channels"></p>', `<p id="foot-channels">Our YouTube channels: ${channelLinks(channelUrl)}</p>`)
  .replace('<span id="year"></span>', `<span id="year">${new Date().getFullYear()}</span>`);

// Beehiiv's form, "Opening…" on affiliate links (as on the home page), and the year.
const SCRIPT = `(function () {
  var FORM = ${JSON.stringify(NEWSLETTER.beehiivForm || "")};
  // Subscribers see no sign-up box or header field (as on index.html: Beehiiv's cookie, or the note "ul-subscribed" that
  // this browser keeps after confirming or "Already subscribed? Hide this"; it never leaves the device).
  function hideSignup() {
    var hj = document.getElementById("header-join");
    if (hj) hj.style.display = "none";
    [].forEach.call(document.querySelectorAll("section.newsletter"), function (s) { s.remove(); });
  }
  var subscribed = /(^|; )bhv_[^=]+_subscribed=/.test(document.cookie);
  try { subscribed = subscribed || localStorage.getItem("ul-subscribed") === "1"; } catch (e) {}
  if (subscribed) hideSignup();
  document.addEventListener("click", function (e) {
    if (!e.target.closest || !e.target.closest(".nl-hide")) return;
    try { localStorage.setItem("ul-subscribed", "1"); } catch (err) {}
    hideSignup();
  });
  [].forEach.call(document.querySelectorAll(".bh-slot"), function (slot) {
    if (!FORM || subscribed) return;
    if (/(^|; )bhv_[^=]+_subscribed=/.test(document.cookie)) {
      var p = document.createElement("p"); p.className = "joined"; p.textContent = "You're subscribed. Thanks!";
      slot.parentNode.replaceChild(p, slot); return;
    }
    var s = document.createElement("script");
    s.async = true; s.src = "https://subscribe-forms.beehiiv.com/v3/loader.js"; s.setAttribute("data-beehiiv-form", FORM);
    slot.appendChild(s);
    setTimeout(function () { slot.classList.add("slow"); }, 5000);
  });
  [].forEach.call(document.querySelectorAll(".jrow button"), function (b) {
    b.form.addEventListener("submit", function () { b.textContent = "Opening\\u2026"; });
  });
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest('a[rel~="sponsored"]');
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || a.target === "_blank") return;
    if (a.classList.contains("visit")) { a.dataset.label = a.textContent; a.textContent = "Opening\\u2026"; }
    a.classList.add("opening");
  });
  window.addEventListener("pageshow", function () {
    [].forEach.call(document.querySelectorAll(".opening"), function (a) {
      a.classList.remove("opening");
      if (a.dataset.label) a.textContent = a.dataset.label;
    });
  });
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();
  // A/B test of the "Work with us" strip (version B) on about half of all page views; nothing is stored. With the strip,
  // the footer's Work with us link is counted as /c-work-b, so both versions' clicks per page view can be compared.
  var w = document.getElementById("wwu");
  if (w && Math.random() < 0.5) {
    w.hidden = false;
    var fw = document.querySelector('footer a[href="/c-work"]');
    if (fw) fw.setAttribute("href", "/c-work-b");
  }
})();`;

// Beehiiv's field loads sooner with these; subscribers see no field, so their browser doesn't contact Beehiiv at all.
const beehiivHead = !(NEWSLETTER.ready && NEWSLETTER.beehiivForm) ? "" :
  `<script>(function () {
  var s = /(^|; )bhv_[^=]+_subscribed=/.test(document.cookie);
  try { s = s || localStorage.getItem("ul-subscribed") === "1"; } catch (e) {}
  if (s) return;
  [["preconnect", "https://subscribe-forms.beehiiv.com"], ["preload", "https://subscribe-forms.beehiiv.com/v3/loader.js", "script"],
   ["preload", "https://subscribe-forms.beehiiv.com/api/v3/forms/${esc(NEWSLETTER.beehiivForm)}", "fetch", 1]].forEach(function (x) {
    var l = document.createElement("link"); l.rel = x[0]; l.href = x[1];
    if (x[2]) l.as = x[2];
    if (x[3]) l.crossOrigin = "anonymous";
    document.head.appendChild(l);
  });
})();</script>
`;

function crumbsLd(items) {
  return { "@context": "https://schema.org", "@type": "BreadcrumbList",
    itemListElement: items.map((it, i) => ({ "@type": "ListItem", position: i + 1, name: it.name, item: SITE + "/" + it.path })) };
}
function crumbsHtml(items) {
  return '<nav class="crumbs" aria-label="Breadcrumb">' +
    items.map((it, i) => i === items.length - 1 ? `<span aria-current="page">${esc(it.name)}</span>` : `<a href="/${it.path}">${esc(it.name)}</a>`)
      .join(" › ") + "</nav>";
}
const HOME = { name: "Home", path: "" };
// The category list moved from the home page to How-tos (1 Nov 2026: the home page is now app news).
const HOWTOS = { name: "How-tos", path: "how-tos/" }, NEWSL = { name: "News", path: "news/" };

function layout(p) {
  const url = SITE + "/" + p.path;
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
${beehiivHead}<title>${esc(p.title)}</title>
<meta name="description" content="${esc(p.description)}">
<link rel="canonical" href="${url}">
${p.nav === "news" ? '<link rel="alternate" type="application/rss+xml" title="Use &amp; Like app news" href="/news/feed.xml">\n' : ""}${p.noindex ? '<meta name="robots" content="noindex, follow">\n' : ""}<meta property="og:type" content="website">
<meta property="og:site_name" content="Use &amp; Like">
<meta property="og:title" content="${esc(p.title)}">
<meta property="og:description" content="${esc(p.description)}">
<meta property="og:url" content="${url}">
${(p.share || DEFAULT_SHARE) ? `<meta property="og:image" content="${SITE}${p.share || DEFAULT_SHARE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="${esc(p.shareAlt || "Use & Like: app news, deals and how-tos")}">
<meta name="twitter:card" content="summary_large_image">
` : ""}${p.noindex ? "" : '<meta name="robots" content="max-image-preview:large">\n'}<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#1f3a5f">
${ICON}
${p.jsonld.map(ld).join("\n")}
<style>${STYLE}</style>
</head>
<body>
<div class="wrap">
  ${header(p.nav)}

  <main class="${p.cls}">
${p.main}
  </main>

  ${footer()}
</div>
<script>
${SCRIPT}
</script>
${p.script ? `<script>\n${p.script}\n</script>\n` : ""}</body>
</html>
`;
}

function card(v) {
  const img = hasThumb(v.id) ? `<img src="/thumbs/${v.id}.jpg" alt="" loading="lazy" width="320" height="180">` : "";
  return `<li class="vcard"><a href="https://www.youtube.com/watch?v=${v.id}"${newTab}>${img}<p class="vt">${esc(v.title)}</p>` +
    `<p class="vm">${esc([v.tool, v.channel].filter(Boolean).join(" · "))}</p></a></li>`;
}
const grid = list => `<ul class="plain vgrid">\n${list.map(card).join("\n")}\n</ul>`;
function toolRow(t, moreLink) {
  const n = toolVideos.get(t.name).length;
  return `<li class="row"><div class="main"><a class="name" href="/${t.slug}" ${sponsored}>${esc(t.name)}</a>` +
    (t.isPick ? '<span class="pick">Our pick</span>' : "") + `<p class="desc">${esc(t.description)}</p>` +
    (t.why ? `<p class="note">${esc(t.why)}</p>` : "") + (t.details ? `<p class="note">${esc(t.details)}</p>` : "") +
    (moreLink ? `<p class="tool-more"><a href="/${toolPath(t)}">${n ? esc(plural(n, "video")) + " and more about " + esc(t.name) : "More about " + esc(t.name)} ›</a></p>` : "") +
    `</div><a class="visit" href="/${t.slug}" ${sponsored} aria-label="Visit ${esc(t.name)}">Visit</a></li>`;
}

// ---- Pages ----
const out = new Map();   // relative file path -> content
const sitemap = [""];

const CAT_TOP = 12;      // videos shown on a category page
const TOOL_FIRST = 24;   // videos shown on a tool page before "Show all"

for (const cat of CATEGORIES) {
  const tools = toolsIn(cat), vids = catVideos.get(cat), p = catPath(cat);
  const names = tools.map(t => t.name);
  const nameList = names.length > 1 ? names.slice(0, -1).join(", ") + " and " + names[names.length - 1] : names.join("");
  const main = [
    crumbsHtml([HOWTOS, { name: cat, path: p }]),
    `<h1>${esc(cat)}</h1>`,
    `<p class="count">${tools.length ? esc(plural(tools.length, "tool")) + (vids.length ? " · " + esc(plural(vids.length, "video")) : "") : "Coming soon"}</p>`,
    `<ul class="plain rows">\n${tools.map(t => toolRow(t, true)).join("\n")}\n</ul>`,
    vids.length ? `<h2 class="vsub">Our videos about ${esc(cat)}</h2>\n${grid(vids.slice(0, CAT_TOP))}` : "",
    vids.length ? `<p class="more-videos">Want more? <a href="/#videos-${slugOf(cat)}">All ${esc(plural(vids.length, "video"))} about ${esc(cat)} ›</a></p>` : "",
    newsletterBox()
  ].filter(Boolean).join("\n");
  out.set(p + "index.html", layout({
    path: p, nav: "howtos", cls: "page",
    title: `${cat}: ${plural(tools.length, "tool")}${vids.length ? " and " + plural(vids.length, "video tutorial") : ""} | Use & Like`,
    description: `${cat} on Use & Like: ${nameList}.` + (vids.length ? ` ${plural(vids.length, "video tutorial")} from our channels.` : ""),
    noindex: !catIndexed(cat),
    jsonld: [crumbsLd([HOWTOS, { name: cat, path: p }]), { "@context": "https://schema.org", "@type": "ItemList", name: cat,
      itemListElement: tools.map((t, i) => ({ "@type": "ListItem", position: i + 1, name: t.name, url: SITE + "/" + toolPath(t) })) }],
    main
  }));
  if (catIndexed(cat)) sitemap.push(p);
}

for (const t of TOOLS) {
  const vids = toolVideos.get(t.name), p = toolPath(t), cp = catPath(t.category);
  const others = toolsIn(t.category).filter(x => x !== t);
  const trail = [HOWTOS, { name: t.category, path: cp }, { name: t.name, path: p }];
  const main = [
    crumbsHtml(trail),
    `<div class="tool-head"><div class="main"><h1>${esc(t.name)}${t.isPick ? ' <span class="pick">Our pick</span>' : ""}</h1>` +
      `<p class="lead">${esc(t.description)}</p>` + (t.why ? `<p class="note">${esc(t.why)}</p>` : "") +
      (t.details ? `<p class="note">${esc(t.details)}</p>` : "") +
      `</div><a class="visit big-cta" href="/${t.slug}" ${sponsored}>Visit ${esc(t.name)} ›</a></div>`,
    vids.length ? `<h2 class="vsub">Our videos about ${esc(t.name)} (${vids.length})</h2>\n${grid(vids.slice(0, TOOL_FIRST))}` +
      (vids.length > TOOL_FIRST ? `\n<details class="more-vids"><summary>Show all ${vids.length} videos</summary>\n${grid(vids.slice(TOOL_FIRST))}\n</details>` : "")
      : `<p class="search-on">${PLAY}Search our channels for ${esc(t.name)}: ${channelLinks(c => channelUrl(c) + "/search?query=" + encodeURIComponent(t.name))}</p>`,
    others.length ? `<h2 class="vsub">Other ${esc(t.category)} tools</h2>\n<ul class="plain related">\n` +
      others.map(o => `<li><a href="/${toolPath(o)}">${esc(o.name)}</a> – ${esc(o.description)}</li>`).join("\n") +
      `\n</ul>\n<p class="tool-more"><a href="/${cp}">All ${esc(t.category)} tools ›</a></p>` : "",
    newsletterBox()
  ].filter(Boolean).join("\n");
  out.set(p + "index.html", layout({
    path: p, nav: "howtos", cls: "page",
    title: vids.length ? `${t.name}: ${plural(vids.length, "video tutorial")} | Use & Like` : `${t.name} – ${t.description} | Use & Like`,
    description: `${t.name}: ${sentence(t.description)}.` +
      (vids.length ? ` ${plural(vids.length, "video tutorial")} about ${t.name} from our channels` +
        (others.length ? `, and other ${t.category} tools.` : ".") : ""),
    noindex: !toolIndexed(t),
    jsonld: [crumbsLd(trail)],
    main
  }));
  if (toolIndexed(t)) sitemap.push(p);
}

for (const pg of PAGES) {
  const trail = [HOME, { name: pg.title, path: pg.path }];
  const list = items => items && items.length ? `<ul class="checks">\n${items.map(b => `<li>${rich(b)}</li>`).join("\n")}\n</ul>` : "";
  const paras = items => (items || []).map(x => `<p>${rich(x)}</p>`).join("\n");
  const main = [
    crumbsHtml(trail),
    `<h1>${esc(pg.title)}</h1>`,
    pg.lead ? `<p class="lead">${rich(pg.lead)}</p>` : "",
    paras(pg.paragraphs),
    pg.h2 ? `<h2 class="vsub">${esc(pg.h2)}</h2>` : "",
    list(pg.bullets),
    paras(pg.after),
    pg.channels ? `<p>Our YouTube channels: ${channelLinks(channelUrl)}</p>` : ""
  ].filter(Boolean).join("\n");
  out.set(pg.path + "index.html", layout({
    path: pg.path, nav: "", cls: "page info", title: pg.title + " | Use & Like", description: pg.description,
    noindex: false, jsonld: [crumbsLd(trail)], main
  }));
  sitemap.push(pg.path);
}

// Deals: each card links straight to the brand through our short link (no page in between) and to our tool page.
const toolBySlug = new Map(TOOLS.map(t => [t.slug, t]));
const shortDay = iso => new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
function dealCard(d) {
  const t = toolBySlug.get(d.slug);
  const icon = fs.existsSync(path.join(ROOT, "img", "deals", d.slug + ".webp"))
    ? `<img src="/img/deals/${d.slug}.webp" alt="" width="48" height="48" loading="lazy">`
    : `<span class="deal-letter" aria-hidden="true">${esc(d.brand[0])}</span>`;
  return `<li class="deal"><div class="deal-top">${icon}<span class="deal-brand">${esc(d.brand)}</span></div>` +
    `<p class="deal-big">${esc(d.big)}</p><p class="deal-offer">${esc(d.offer)}</p>` +
    (d.detail ? `<p class="deal-detail">${esc(d.detail)}</p>` : "") +
    `<p class="deal-checked">Checked on ${esc(d.brand)}'s site on ${esc(shortDay(d.checked))}${d.ends ? " · ends " + esc(d.ends) : ""}</p>` +
    `<div class="deal-acts"><a class="visit" href="/${d.slug}" ${sponsored}>Get the deal</a>` +
    (t ? `<a class="deal-more" href="/${toolPath(t)}">About ${esc(t.name)} ›</a>` : "") + "</div></li>";
}
// A partner offer: the brand's own wording from our partner network, its code and where it applies; the whole line goes
// to the brand through our short link.
const dealHead = (id, title) => `<div class="sec-head"><h2 id="${id}">${esc(title)}</h2></div>`;
const groupId = g => g.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
function offerRow(o) {
  return `<li class="po"><a href="/${o.slug}" ${sponsored}><b>${esc(o.brand)}</b><span class="po-text">${esc(o.text)}</span>` +
    `<span class="po-go" aria-hidden="true">›</span></a>` +
    ((o.code || o.where) ? `<span class="po-meta">${o.code ? `Code <code>${esc(o.code)}</code>` : ""}${o.code && o.where ? " · " : ""}${o.where ? esc(o.where) : ""}</span>` : "") +
    "</li>";
}
{
  const p = "deals/", trail = [HOME, { name: "Deals", path: p }];
  // Groups by size, "More" and "Other" last.
  const counts = new Map();
  for (const o of OFFERS) counts.set(o.group, (counts.get(o.group) || 0) + 1);
  const groups = [...counts.keys()].sort((a, b) => (/^(More|Other)$/.test(a) - /^(More|Other)$/.test(b)) || counts.get(b) - counts.get(a) || a.localeCompare(b));
  const seen = PARTNER.updated ? shortDay(PARTNER.updated) : "";
  const partner = OFFERS.length ? [
    `<section aria-labelledby="po-h">${dealHead("po-h", "More offers from our partners")}`,
    `<p class="note">${esc(OFFERS.length)} offers as the brands list them on our partner network${seen ? `, seen there on ${esc(seen)}` : ""}. ` +
      "They change often: check the final price on the brand's site before you pay.</p>",
    `<div class="po-chips" role="group" aria-label="Show offers for"><button type="button" class="on" data-g="">All ${esc(OFFERS.length)}</button>` +
      groups.map(g => `<button type="button" data-g="${groupId(g)}">${esc(g)} ${esc(counts.get(g))}</button>`).join("") + "</div>",
    groups.map(g => `<section class="po-group" data-g="${groupId(g)}"><h3>${esc(g)}</h3><ul class="plain po-list">` +
      OFFERS.filter(o => o.group === g).map(offerRow).join("") + "</ul></section>").join("\n"),
    "</section>"
  ].join("\n") : "";
  const main = [
    crumbsHtml(trail),
    "<h1>App deals running now</h1>",
    "<p class=\"lead\">Discounts on apps and services we link to: first the deals we checked on each brand's own website, " +
      "then the offers our partner brands list. Prices change, so check the final price before you pay.</p>",
    "<p class=\"note\">These are partner links: if you buy through one, we may earn a commission at no extra cost to you.</p>",
    DEALS.length ? `<section aria-labelledby="dc-h">${dealHead("dc-h", "Deals we checked")}\n<ul class="plain deals">\n${DEALS.map(dealCard).join("\n")}\n</ul></section>`
      : (OFFERS.length ? "" : "<p class=\"count\">No deals running right now. Our newsletter tells you when new ones start.</p>"),
    partner,
    newsletterBox()
  ].filter(Boolean).join("\n");
  const script = OFFERS.length ? `(function () {
  var chips = document.querySelectorAll(".po-chips button"), groups = document.querySelectorAll(".po-group");
  [].forEach.call(chips, function (b) {
    b.addEventListener("click", function () {
      var g = b.getAttribute("data-g");
      [].forEach.call(chips, function (x) { x.classList.toggle("on", x === b); });
      [].forEach.call(groups, function (s) { s.hidden = !!g && s.getAttribute("data-g") !== g; });
    });
  });
})();` : "";
  const total = DEALS.length + OFFERS.length;
  out.set(p + "index.html", layout({
    path: p, nav: "deals", cls: "page", title: total ? `App deals running now: ${total} offers | Use & Like` : "App deals running now | Use & Like",
    description: total ? `Discounts on ${DEALS.map(d => d.brand).join(", ")} checked on each brand's own website, plus ${OFFERS.length} offers from our partner brands in travel, software, VPNs, phone plans and more.`
      : "Running discounts on apps and services, checked on each brand's own website.",
    noindex: !total, jsonld: [crumbsLd(trail)], main, script
  }));
  if (total) sitemap.push(p);
}

// ---- App news, how-tos and the front page (Kevin, 1 Nov 2026: "overall way better", "go") ----
// Stories: data/news/<slug>.json, one file per story (written from the Studio's checked stories; facts only from the
// sources named in the file). Pages: news/<slug>/ per story, news/ (all stories), how-tos/ (search + browse by category),
// and the front page in index.html's "home" block.
const NEWS_DIR = path.join(ROOT, "data", "news");
const NEWS = (fs.existsSync(NEWS_DIR) ? fs.readdirSync(NEWS_DIR).filter(f => f.endsWith(".json")) : []).map(f => {
  const s = JSON.parse(fs.readFileSync(path.join(NEWS_DIR, f), "utf8"));
  for (const k of ["slug", "date", "head", "dek", "sources"]) if (!s[k] || (Array.isArray(s[k]) && !s[k].length)) throw new Error(`data/news/${f}: missing "${k}"`);
  if (f !== s.slug + ".json") throw new Error(`data/news/${f}: the file name should be ${s.slug}.json`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s.date)) throw new Error(`data/news/${f}: "date" should look like 2026-10-28`);
  return s;
}).sort((a, b) => b.date.localeCompare(a.date) || (a.rank || 99) - (b.rank || 99) || a.head.localeCompare(b.head));
const TOP_NEWS = NEWS.filter(s => !s.quick), QUICK_NEWS = NEWS.filter(s => s.quick);
const newsPath = s => "news/" + s.slug + "/";
const longDay = iso => new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const linkOut = (href, text) => `<a href="${esc(href)}"${newTab || ' rel="noopener"'}>${esc(text)}</a>`;
const sourcesLine = s => s.sources.map(x => x.url ? linkOut(x.url, x.name) : esc(x.name)).join(", ");

// Recommended how-tos: most viewed first (videos.js order), only videos with a new thumbnail (Kevin, 1 Nov: "they look
// better"; data/new-thumbs.json), never titles that undercut an offer or are about leaving a service.
const NEW_THUMBS = (() => { try { return JSON.parse(fs.readFileSync(path.join(ROOT, "data", "new-thumbs.json"), "utf8")).videos || {}; } catch (_) { return {}; } })();
const UNDERCUT = /\b(free shopping|coupons?|for free|free alternative|premium free|license key|trial reset|cancel|refund|delete|unsubscribe)\b/i;
const siteVids = (W.CHANNEL_VIDEOS || []).map(r => ({ id: r[0], title: r[1], channel: W.CHANNEL_VIDEO_CHANNELS[r[2]], tool: W.CHANNEL_VIDEO_TOOLS[r[3]] }));
const RECOMMENDED = siteVids.filter(v => NEW_THUMBS[v.id] && hasThumb(v.id) && !UNDERCUT.test(v.title));
const wordRe = w => new RegExp("(^|[^\\w])" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "($|[^\\w])", "i");
// A story's topic -> the site category whose how-tos fit it (when no video names the story's apps).
const TOPIC_CATEGORY = { Privacy: "VPN & Privacy", Security: "VPN & Privacy", AI: "AI Writing & Research", Money: "Money & Trading",
  Shopping: "Shopping & Mobile", Travel: "Travel", Email: "Email", Video: "Video Creation", Business: "Business & Legal" };
function howtosFor(s, n) {
  const picked = (s.howtos || []).map(id => RECOMMENDED.find(v => v.id === id) || siteVids.find(v => v.id === id)).filter(Boolean);
  for (const app of s.apps || []) for (const v of RECOMMENDED) if (picked.length < n && !picked.includes(v) && wordRe(app).test(v.title)) picked.push(v);
  const cat = s.category || TOPIC_CATEGORY[s.topic];
  for (const v of RECOMMENDED) if (picked.length < n && !picked.includes(v) && cat && (toolByName.get(v.tool) || {}).category === cat) picked.push(v);
  for (const v of RECOMMENDED) if (picked.length < n && !picked.includes(v)) picked.push(v);
  return picked.slice(0, n);
}

// A story without a picture of its own shows its apps: their icons (up to 3) on the first app's colour; an app
// without an icon gets its first letter on a colour from its name.
const ART_COLOURS = ["#2b6cb0", "#2f855a", "#b7791f", "#c53030", "#6b46c1", "#2c7a7b", "#b83280", "#4a5568"];
function storyArt(s, cls) {
  const apps = (s.apps || []).filter(a => typeof a === "string");
  const icons = [];
  for (const a of apps) {
    const e = APP_ICONS[a];
    if (e && e.file && !icons.some(x => x.file === e.file) && fs.existsSync(path.join(ROOT, e.file))) icons.push(e);
  }
  const name = apps[0] || s.head;
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  const c = (icons[0] && icons[0].color) || (APP_ICONS[name] || {}).color || ART_COLOURS[hash % ART_COLOURS.length];
  const inner = icons.length
    ? icons.slice(0, 3).map((e, i) => `<img src="/${esc(e.file)}${e.v ? "?v=" + esc(e.v) : ""}" alt="" width="256" height="256"${i ? ' class="b"' : ""} loading="lazy">`).join("")
    : `<b>${esc(name[0])}</b>`;
  return `<span class="art ${cls}" style="--c:${esc(c)}" aria-hidden="true">${inner}</span>`;
}
function storyThumb(s, w) {
  const t = s.thumb || storyPic(s, "-thumb");
  return t ? `<img src="${esc(t)}" alt="" width="${w}" height="${w / 2}" loading="lazy">` : storyArt(s, "sm");
}
// Cards (Kevin, 2 Nov: the picture boxes felt "cut off or not fitting ... maybe we should have just a bigger app logo
// and behind the whole text some light background ... border colored", picked D + D): every story in a list and the
// top story sit on a card in a soft tint of the app's colour, with the app's logo on its own (a second app small on
// its corner; a letter on the app's colour when there is no logo). The colour is the card's --c.
function storyApps(s) {
  const apps = (s.apps || []).filter(a => typeof a === "string"), icons = [];
  for (const a of apps) {
    const e = APP_ICONS[a];
    if (e && e.file && !icons.some(x => x.file === e.file) && fs.existsSync(path.join(ROOT, e.file))) icons.push(e);
  }
  const name = apps[0] || s.head;
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return { icons, name, color: (icons[0] && icons[0].color) || (APP_ICONS[name] || {}).color || ART_COLOURS[hash % ART_COLOURS.length] };
}
function appMark(s, cls) {
  const { icons, name } = storyApps(s);
  const inner = icons.length
    ? icons.slice(0, 2).map((e, i) => `<img src="/${esc(e.file)}${e.v ? "?v=" + esc(e.v) : ""}" alt="" width="256" height="256"${i ? ' class="b"' : ""} loading="lazy">`).join("")
    : `<b>${esc(name[0])}</b>`;
  return `<span class="appmark ${cls}" aria-hidden="true">${inner}</span>`;
}
const cardColour = s => `--c:${esc(storyApps(s).color)}`;
// Rumors, leaks and features in testing (Kevin, 1 Nov: "speculative ... we can frame them exactly like that"): amber tag.
const tagHtml = s => (s.tag || s.rumor) ? `<span class="tag${s.rumor ? " rumor" : ""}">${esc(s.tag || "Rumor")}</span>` : "";
const storyRow = s => `<li style="${cardColour(s)}"><a href="/${newsPath(s)}" tabindex="-1" aria-hidden="true">${appMark(s, "sm")}</a><div>` +
  tagHtml(s) + `<h3><a href="/${newsPath(s)}">${esc(s.head)}</a></h3>` +
  `<p class="one">${esc(s.means || s.dek)}</p><p class="meta">${esc(shortDay(s.date))} · ${esc(s.sources.map(x => x.name).join(", "))}</p></div></li>`;
const storyRows = list => `<ul class="plain srows">\n${list.map(storyRow).join("\n")}\n</ul>`;
const oneLine = list => `<ul class="plain one-line">\n${list.map(s => `<li><b><a href="/${newsPath(s)}">${esc(s.head)}</a></b>` +
  `<span>${esc(s.dek)}</span><span class="meta">${esc(shortDay(s.date))} · ${sourcesLine(s)}</span></li>`).join("\n")}\n</ul>`;
const dealMini = d => `<li class="dmini"><a href="/${d.slug}" ${sponsored}><span class="top">` +
  (fs.existsSync(path.join(ROOT, "img", "deals", d.slug + ".webp")) ? `<img src="/img/deals/${d.slug}.webp" alt="" width="30" height="30" loading="lazy">` : "") +
  `${esc(d.brand)}</span><span class="big">${esc(d.big)}</span><span class="offer">${esc(d.offer)}</span>` +
  `<span class="chk">Checked on ${esc(d.brand)}'s site, ${esc(shortDay(d.checked))}</span></a></li>`;
const dealMinis = list => `<ul class="plain dminis">\n${list.map(dealMini).join("\n")}\n</ul>`;
const secHead = (id, title, link) => `<div class="sec-head"><h2 id="${id}">${esc(title)}</h2>${link || ""}</div>`;

// Story pages: what happened, what it means for you, what to do, the details, our how-tos, deals, more stories.
for (const s of NEWS) {
  const p = newsPath(s), trail = [HOME, NEWSL, { name: s.head, path: p }];
  const others = TOP_NEWS.filter(x => x !== s).slice(0, 3);
  const main = [
    crumbsHtml(trail),
    '<article class="story" aria-labelledby="story-h">',
    tagHtml(s) + `<h1 id="story-h">${esc(s.head)}</h1>`,
    `<p class="dek">${esc(s.dek)}</p>`,
    s.rumor ? '<p class="unconfirmed"><strong>Not confirmed.</strong> This comes from a report, a leak or a test version, not from the company itself, so details can still change.</p>' : "",
    `<p class="meta">Use &amp; Like · ${esc(longDay(s.date))} · Source: ${sourcesLine(s)}</p>`,
    (s.image || storyPic(s, "-art")) ? `<img class="hero" src="${esc(s.image || storyPic(s, "-art"))}" alt="" width="1200" height="600">` : storyArt(s, "big"),
    s.means ? `<div class="callout"><h2>What it means for you</h2><p>${esc(s.means)}</p></div>` : "",
    s.todo ? `<div class="todo"><h2>What to do</h2><p>${esc(s.todo)}</p></div>` : "",
    s.details && !s.details_in_todo ? `<div class="details"><h2>The details</h2><p>${esc(s.details)}</p>` +
      (s.where ? `<p class="meta">Where and when: ${esc(s.where)}</p>` : "") + "</div>" : (s.where ? `<p class="meta">Where and when: ${esc(s.where)}</p>` : ""),
    s.video ? `<p class="watch"><a class="visit" href="https://www.youtube.com/watch?v=${esc(s.video)}"${newTab}>${PLAY} Watch our video about this</a></p>` : "",
    newsletterBox(),
    `<section aria-labelledby="ht-h">${secHead("ht-h", "How-tos from our channels", '<a href="/how-tos/">Search all how-tos ›</a>')}\n${grid(howtosFor(s, 3))}</section>`,
    DEALS.length ? `<section aria-labelledby="dl-h">${secHead("dl-h", "Deals we checked", `<a href="/deals/">All ${DEALS.length} ›</a>`)}\n${dealMinis(DEALS.slice(0, 4))}</section>` : "",
    others.length ? `<section aria-labelledby="mn-h">${secHead("mn-h", "More app news", '<a href="/news/">All app news ›</a>')}\n${storyRows(others)}</section>` : "",
    `<p class="src">We write every story in our own words from its source and check the facts before it goes up. Source: ${sourcesLine(s)}.</p>`,
    "</article>"
  ].filter(Boolean).join("\n");
  const article = { "@context": "https://schema.org", "@type": "NewsArticle", headline: s.head, description: s.dek,
    datePublished: s.date, dateModified: s.updated || s.date, mainEntityOfPage: SITE + "/" + p,
    author: { "@type": "Organization", name: "Use & Like", url: SITE + "/" },
    publisher: { "@type": "Organization", name: "Use & Like", url: SITE + "/" } };
  const share = storyPic(s, "");
  if (s.image || share) article.image = [SITE + (s.image || share)];
  out.set(p + "index.html", layout({
    path: p, nav: "news", cls: "page", title: `${s.head} | Use & Like`, description: s.dek.slice(0, 300),
    noindex: false, jsonld: [crumbsLd(trail), article], main, share, shareAlt: s.head
  }));
  sitemap.push(p);
}

// All stories, newest first.
if (NEWS.length) {
  const p = NEWSL.path, trail = [HOME, NEWSL];
  out.set(p + "index.html", layout({
    path: p, nav: "news", cls: "page", title: "App news | Use & Like",
    description: "What changed in the apps you use, in our own words, with what it means for you and what to do about it.",
    noindex: false, jsonld: [crumbsLd(trail)],
    main: [crumbsHtml(trail), "<h1>App news</h1>",
      '<p class="lead">What changed in the apps you use, in our own words, with what it means for you and what to do about it.</p>',
      storyRows(TOP_NEWS), QUICK_NEWS.length ? `<section aria-labelledby="ol-h">${secHead("ol-h", "In one line")}\n${oneLine(QUICK_NEWS)}</section>` : "",
      newsletterBox()].filter(Boolean).join("\n")
  }));
  sitemap.push(p);
  // RSS feed (newest 50 stories) for feed readers and news apps.
  const x = v => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  out.set("news/feed.xml", `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<title>Use &amp; Like: app news</title>
<link>${SITE}/news/</link>
<atom:link href="${SITE}/news/feed.xml" rel="self" type="application/rss+xml"/>
<description>What changed in the apps you use, in our own words, with what it means for you and what to do about it.</description>
<language>en</language>
${NEWS.slice(0, 50).map(s => `<item><title>${x(s.head)}</title><link>${SITE}/${newsPath(s)}</link><guid isPermaLink="true">${SITE}/${newsPath(s)}</guid>` +
  `<pubDate>${new Date(s.date + "T12:00:00Z").toUTCString()}</pubDate><description>${x(s.dek)}</description></item>`).join("\n")}
</channel>
</rss>
`);
}

// How-tos: search over all our videos (how-tos/search.json, loaded on the first search), then browse by category.
{
  const rows = fs.readFileSync(path.join(ROOT, "data", "channel-videos.tsv"), "utf8").split("\n").map(l => l.split("\t")).filter(r => r.length >= 5);
  const chans = [...new Set(rows.map(r => r[4].trim()))];
  // No Shorts (60 seconds or less), no titles that undercut an offer; most viewed first.
  const vids = rows.filter(r => /^[\w-]{11}$/.test(r[0]) && !(+r[2] > 0 && +r[2] <= 60) && !UNDERCUT.test(r[3]))
    .sort((a, b) => (+b[1] || 0) - (+a[1] || 0)).map(r => [r[0], r[3], chans.indexOf(r[4].trim())]);
  out.set("how-tos/search.json", JSON.stringify({ channels: chans, videos: vids,
    tools: TOOLS.map(t => [t.name, t.slug, t.category]), news: NEWS.map(s => [s.slug, s.head, s.date]),
    deals: DEALS.map(d => [d.slug, d.brand, d.offer]).concat(OFFERS.map(o => [o.slug, o.brand, o.text])) }));
  const p = HOWTOS.path, trail = [HOME, HOWTOS];
  // Kevin, 1 Nov: "browse by category ... doesn't look clean enough maybe have just the search bar": the search leads;
  // the categories are one quiet line of links under it (the big grid of tool links is gone from this page).
  const cats = '<ul class="plain catline">' + CATEGORIES.filter(cat => toolsIn(cat).length).map(cat =>
    `<li><a href="/${catPath(cat)}">${esc(cat)}</a></li>`).join("") + "</ul>";
  const chips = ["Wise", "Shein", "WhatsApp", "Netflix", "Proton VPN", "CapCut", "ChatGPT", "TikTok"];
  const main = [
    crumbsHtml(trail),
    '<div class="howtos">',
    '<section class="hs" aria-labelledby="hs-h"><h1 id="hs-h">What app do you need help with?</h1>' +
      `<p class="lead">Search ${esc(vids.length.toLocaleString("en-US"))} how-to videos from our channels, our app news and the deals we checked.</p>` +
      '<div class="sbox"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>' +
      '<input id="q" type="search" placeholder="Try Wise, CapCut, VPN, ChatGPT..." autocomplete="off" aria-label="Search our how-tos, news and deals" aria-controls="res"></div>' +
      `<div class="qchips" role="group" aria-label="Popular searches">${chips.map(c => `<button type="button" data-q="${esc(c)}">${esc(c)}</button>`).join("")}</div>` +
      '<div class="results" id="res" aria-live="polite" hidden></div></section>',
    RECOMMENDED.length ? `<section aria-labelledby="hp-h">${secHead("hp-h", "How-tos people watch")}\n${grid(RECOMMENDED.slice(0, 8))}</section>` : "",
    `<section class="cats" aria-labelledby="bc-h"><h2 id="bc-h">Or browse by category</h2>${cats}</section>`,
    newsletterBox(),
    "</div>"
  ].filter(Boolean).join("\n");
  const script = `(function () {
  var q = document.getElementById("q"), res = document.getElementById("res"), data = null, waiting = [];
  var NEW_TAB = ${JSON.stringify(!!OPEN_IN_NEW_TAB)};
  function load(then) {
    if (data) return then();
    waiting.push(then);
    if (waiting.length > 1) return;
    fetch("/how-tos/search.json").then(function (r) { return r.json(); }).then(function (d) {
      data = d; var w = waiting; waiting = []; w.forEach(function (f) { f(); });
    }).catch(function () { waiting = []; res.hidden = false; res.textContent = "The search didn't load. Check your connection and try again."; });
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function hi(t, w) { var i = t.toLowerCase().indexOf(w); return i < 0 ? esc(t) : esc(t.slice(0, i)) + "<mark>" + esc(t.slice(i, i + w.length)) + "</mark>" + esc(t.slice(i + w.length)); }
  function a(href, html, ext, rel) { return '<a href="' + esc(href) + '"' + (ext && NEW_TAB ? ' target="_blank" rel="noopener' + (rel ? " " + rel : "") + '"' : (rel ? ' rel="' + rel + '"' : "")) + ">" + html + "</a>"; }
  function run() {
    var raw = q.value.trim(), w = raw.toLowerCase();
    if (w.length < 2) { res.hidden = true; res.innerHTML = ""; return; }
    load(function () {
      if (q.value.trim().toLowerCase() !== w) return;
      var words = w.split(/\\s+/), first = words[0];
      var has = function (t) { t = String(t).toLowerCase(); return words.every(function (x) { return t.indexOf(x) >= 0; }); };
      var news = data.news.filter(function (n) { return has(n[1]); }).slice(0, 3);
      var deals = data.deals.filter(function (d) { return has(d[1] + " " + d[2]); }).slice(0, 3);
      var tools = data.tools.filter(function (t) { return has(t[0] + " " + t[2]); }).slice(0, 4);
      var vids = data.videos.filter(function (v) { return has(v[1]); });
      var h = "";
      if (news.length) h += "<div><h3>App news</h3><ul>" + news.map(function (n) { return "<li>" + a("/news/" + n[0] + "/", hi(n[1], first)) + "</li>"; }).join("") + "</ul></div>";
      if (deals.length) h += "<div><h3>Deals</h3><ul>" + deals.map(function (d) { return "<li>" + a("/" + d[0], hi(d[1], first) + ": " + esc(d[2]), true, "sponsored") + "</li>"; }).join("") + "</ul></div>";
      if (tools.length) h += "<div><h3>On our site</h3><ul>" + tools.map(function (t) { return "<li>" + a("/tool/" + t[1] + "/", hi(t[0], first)) + " <span>" + esc(t[2]) + "</span></li>"; }).join("") + "</ul></div>";
      if (vids.length) h += "<div><h3>How-to videos (" + vids.length.toLocaleString("en-US") + ")</h3><ul>" + vids.slice(0, 8).map(function (v) {
        return "<li>" + a("https://www.youtube.com/watch?v=" + v[0], hi(v[1], first), true) + " <span>" + esc(data.channels[v[2]] || "") + "</span></li>"; }).join("") + "</ul>" +
        (vids.length > 8 ? '<p class="more-hits"><button type="button" id="more-hits">Show ' + Math.min(vids.length - 8, 40) + " more</button></p>" : "") + "</div>";
      if (!h) h = "<p>Nothing found for \\u201c" + esc(raw) + "\\u201d. Try the app's name, or pick a category below.</p>";
      res.innerHTML = h; res.hidden = false;
      var more = document.getElementById("more-hits");
      if (more) more.addEventListener("click", function () {
        var ul = more.parentNode.previousSibling;
        vids.slice(8, 48).forEach(function (v) { var li = document.createElement("li"); li.innerHTML = a("https://www.youtube.com/watch?v=" + v[0], hi(v[1], first), true) + " <span>" + esc(data.channels[v[2]] || "") + "</span>"; ul.appendChild(li); });
        more.parentNode.remove();
      });
    });
  }
  q.addEventListener("input", run);
  q.addEventListener("focus", function () { load(function () {}); }, { once: true });
  [].forEach.call(document.querySelectorAll(".qchips button"), function (b) {
    b.addEventListener("click", function () { q.value = b.getAttribute("data-q"); run(); q.focus(); });
  });
})();`;
  out.set(p + "index.html", layout({
    path: p, nav: "howtos", cls: "page", title: "How-tos: search our videos, browse by category | Use & Like",
    description: `Search ${vids.length.toLocaleString("en-US")} how-to videos from How To Rocket, Guide Glimpse and Logic Protocol, or browse the apps and tools we use by category.`,
    noindex: false, jsonld: [crumbsLd(trail)], main, script
  }));
  sitemap.push(p);
}

// The front page (index.html's "home" block): lead story, latest news beside the deals, the newsletter box (the page's
// script puts it into [data-join]), one-liners, how-tos people watch.
// A text's first sentence and the rest: a split at ". " / "! " / "? " before a capital letter or a quote, so "iOS 26.1"
// and "U.S. users" stay whole.
function splitFirst(text) {
  const m = /^(.+?[.!?])\s+(?=[A-Z"“‘(])(.+)$/s.exec(text || "");
  return m ? [m[1], m[2]] : [text || "", ""];
}

function frontPage() {
  // The lead: the newest story with rank 1 from the last 3 days (the daily run gives rank 1 only to a story worth
  // leading the front page), else the newest story; with its picture when it has one, else as a text block.
  const leadFrom = TOP_NEWS.length ? new Date(Date.parse(TOP_NEWS[0].date + "T00:00:00Z") - 2 * 864e5).toISOString().slice(0, 10) : "";
  const lead = TOP_NEWS.find(s => s.rank === 1 && s.date >= leadFrom) || TOP_NEWS[0];
  if (!lead) return "";
  const latest = TOP_NEWS.filter(s => s !== lead).slice(0, 6);
  // The top story on a card like the list's (Kevin, 2 Nov: "D + D"); the picture styles of leadPicture() stay drawn by
  // story-pictures.js for a later A/B test (data-lead-style says which one a page shows).
  // Its text is the dek only, and on phones only the dek's first sentence (Kevin, 2 Nov: "just a short line to
  // understand the base of the story makes more sense nobody likes clutter or wall of texts"); the rest is on its page.
  const [first, rest] = splitFirst(lead.dek);
  return [
    '<div class="front">',
    '<h1 class="sr-only">Use &amp; Like: app news, deals and how-tos</h1>',
    `<section class="lead-story card" style="${cardColour(lead)}" data-lead-style="card" aria-labelledby="lead-h">` +
      `<a href="/${newsPath(lead)}" tabindex="-1" aria-hidden="true">${appMark(lead, "lg")}</a>` +
      `<div class="txt">${tagHtml(lead)}<h2 id="lead-h"><a href="/${newsPath(lead)}">${esc(lead.head)}</a></h2>` +
      `<p class="dek">${esc(first)}${rest ? `<span class="more"> ${esc(rest)}</span>` : ""}</p>` +
      `<p class="meta">${esc(shortDay(lead.date))} · Source: ${esc(lead.sources.map(x => x.name).join(", "))}</p></div></section>`,
    '<div class="split">',
    `<section aria-labelledby="latest-h">${secHead("latest-h", "Latest app news", '<a href="/news/">All app news ›</a>')}\n${storyRows(latest)}` +
      // Kevin, 2 Nov: "after scrolling through the news lines there should be a more stories ... button at the end"
      `\n<a class="more-btn" href="/news/">More stories ›</a></section>`,
    DEALS.length ? `<section aria-labelledby="rail-h">${secHead("rail-h", "Deals we checked", `<a href="/deals/">All ${DEALS.length} ›</a>`)}\n${dealMinis(DEALS.slice(0, 6))}</section>` : "",
    "</div>",
    '<div data-join></div>',
    QUICK_NEWS.length ? `<section aria-labelledby="ol-h">${secHead("ol-h", "In one line")}\n${oneLine(QUICK_NEWS.slice(0, 3))}</section>` : "",
    RECOMMENDED.length ? `<section aria-labelledby="hw-h">${secHead("hw-h", "How-tos people watch", '<a href="/how-tos/">Search all how-tos ›</a>')}\n${grid(RECOMMENDED.slice(0, 4))}</section>` : "",
    "</div>"
  ].filter(Boolean).join("\n");
}

out.set("sitemap.xml", `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemap.map(p => `  <url><loc>${SITE}/${p}</loc></url>`).join("\n")}
</urlset>
`);
out.set("robots.txt", `User-agent: *
Allow: /

Sitemap: ${SITE}/sitemap.xml
`);

// index.html: structured data and the category list as plain HTML (the page's script replaces it with the same list).
const siteLd = { "@context": "https://schema.org", "@graph": [
  { "@type": "Organization", "@id": SITE + "/#organization", name: "Use & Like", url: SITE + "/",
    sameAs: CHANNELS.map(channelUrl) },
  { "@type": "WebSite", "@id": SITE + "/#website", name: "Use & Like", url: SITE + "/",
    publisher: { "@id": SITE + "/#organization" } }
] };
function replaceBlock(html, name, content) {
  const re = new RegExp(`(<!-- build-pages:${name} -->)[\\s\\S]*?(<!-- /build-pages:${name} -->)`);
  if (!re.test(html)) throw new Error(`index.html has no <!-- build-pages:${name} --> markers`);
  return html.replace(re, (m, a, b) => `${a}\n${content}\n${b}`);
}
let newIndex = replaceBlock(indexHtml, "ld", ld(siteLd));
newIndex = replaceBlock(newIndex, "home", frontPage());
out.set("index.html", newIndex);

// ---- Write, or compare with what's there ----
const stale = [];
for (const [rel, content] of out) {
  const file = path.join(ROOT, rel);
  const old = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : null;
  // The year in the footer changes on New Year's Day; that alone doesn't make a page out of date.
  const norm = s => s && s.replace(/<span id="year">\d{4}<\/span>/, '<span id="year"></span>');
  if (norm(old) === norm(content)) continue;
  stale.push(rel);
  if (!CHECK) { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, content); }
}
// Pages of tools or categories that no longer exist.
for (const dir of ["tool", "category", "news"]) {
  const base = path.join(ROOT, dir);
  if (!fs.existsSync(base)) continue;
  for (const name of fs.readdirSync(base)) {
    if (!fs.statSync(path.join(base, name)).isDirectory() || out.has(`${dir}/${name}/index.html`)) continue;
    stale.push(`${dir}/${name}/ (removed)`);
    if (!CHECK) fs.rmSync(path.join(base, name), { recursive: true, force: true });
  }
}
const indexed = sitemap.length;
if (CHECK) {
  if (stale.length) {
    console.log(`Out of date (run node scripts/build-pages.js): ${stale.slice(0, 10).join(", ")}${stale.length > 10 ? ` and ${stale.length - 10} more` : ""}`);
    process.exit(1);
  }
  console.log(`Pages are up to date (${out.size - 3} pages, ${indexed} in the sitemap).`);
} else {
  console.log(`${stale.length ? `Wrote ${stale.length} file(s).` : "Nothing changed."} ${CATEGORIES.length} category pages, ` +
    `${TOOLS.length} tool pages, ${PAGES.length} other pages, deals page (${DEALS.length} deals), ${NEWS.length} stories, how-tos page; ${indexed} pages in the sitemap ` +
    `(noindex for now: ${TOOLS.filter(t => !toolIndexed(t)).map(t => t.name).concat(CATEGORIES.filter(c => !catIndexed(c))).join(", ") || "none"}).`);
}
