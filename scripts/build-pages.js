#!/usr/bin/env node
// Builds the real pages of useandlike.com, so search engines and AI assistants find a page per category and per tool
// (the home page and the Videos tab stay as they are). Everything comes from the EDIT HERE block of index.html,
// videos.js and the texts below:
//   category/<category>/index.html   the category's tools with Visit buttons, and our most viewed videos about them
//   tool/<slug>/index.html           what the tool does, Visit button, all our videos about it, the other tools
//   about/ how-we-choose/ how-we-make-money/ work-with-us/   (texts in PAGES below)
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
  const note = withPerk ? "" : '<p class="bh-note">After you subscribe, we email you a confirmation link: tap it to finish ' +
    '(check spam too). Field not showing? <a href="/newsletter">Sign up here</a>.</p>';
  if (NEWSLETTER.beehiivForm) return `<div class="join-form">${perk}<div class="bh-slot"></div>${note}</div>`;
  return `<div class="join-form">${perk}<form action="/newsletter" method="get"><div class="jrow">` +
    `<input type="email" name="email" required placeholder="Your email" autocomplete="email" aria-label="Your email">` +
    `<button type="submit">${esc(NEWSLETTER.button)}</button></div></form></div>`;
}
const newsletterBox = () => !NEWSLETTER.ready ? "" : `<section class="newsletter"><div class="nl-text"><h2>${esc(NEWSLETTER.title)}</h2>` +
  `<p>${esc(NEWSLETTER.text)}</p><p class="nl-perk"><span class="perk-gift">${esc(NEWSLETTER.perkGift + " (" + NEWSLETTER.perkSite + ")")}</span></p></div>` +
  joinForm(false) + "</section>";

function header(current) {
  let h = HEADER.replace(/href="#"/g, 'href="/"').replace(/href="#videos"/g, 'href="/#videos"')
    .replace('<div class="ctas" id="header-join"></div>', `<div class="ctas" id="header-join">${NEWSLETTER.ready ? joinForm(true) : ""}</div>`);
  if (current === "tools") h = h.replace('id="nav-tools"', 'id="nav-tools" aria-current="page"');
  return h;
}
const footer = () => FOOTER.replace('<p id="foot-channels"></p>', `<p id="foot-channels">Our YouTube channels: ${channelLinks(channelUrl)}</p>`)
  .replace('<span id="year"></span>', `<span id="year">${new Date().getFullYear()}</span>`);

// Beehiiv's form, "Opening…" on affiliate links (as on the home page), and the year.
const SCRIPT = `(function () {
  var FORM = ${JSON.stringify(NEWSLETTER.beehiivForm || "")};
  [].forEach.call(document.querySelectorAll(".bh-slot"), function (slot) {
    if (!FORM) return;
    if (/(^|; )bhv_[^=]+_subscribed=/.test(document.cookie)) {
      var p = document.createElement("p"); p.className = "joined"; p.textContent = "You're subscribed. Thanks!";
      slot.parentNode.replaceChild(p, slot); return;
    }
    var s = document.createElement("script");
    s.async = true; s.src = "https://subscribe-forms.beehiiv.com/v3/loader.js"; s.setAttribute("data-beehiiv-form", FORM);
    slot.appendChild(s);
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
})();`;

const beehiivHead = !(NEWSLETTER.ready && NEWSLETTER.beehiivForm) ? "" :
  `<link rel="preconnect" href="https://subscribe-forms.beehiiv.com">
<link rel="preload" href="https://subscribe-forms.beehiiv.com/v3/loader.js" as="script">
<link rel="preload" href="https://subscribe-forms.beehiiv.com/api/v3/forms/${esc(NEWSLETTER.beehiivForm)}" as="fetch" crossorigin>
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
const HOME = { name: "All categories", path: "" };

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
${p.noindex ? '<meta name="robots" content="noindex, follow">\n' : ""}<meta property="og:type" content="website">
<meta property="og:site_name" content="Use &amp; Like">
<meta property="og:title" content="${esc(p.title)}">
<meta property="og:description" content="${esc(p.description)}">
<meta property="og:url" content="${url}">
<meta name="color-scheme" content="light dark">
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
</body>
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
    crumbsHtml([HOME, { name: cat, path: p }]),
    `<h1>${esc(cat)}</h1>`,
    `<p class="count">${tools.length ? esc(plural(tools.length, "tool")) + (vids.length ? " · " + esc(plural(vids.length, "video")) : "") : "Coming soon"}</p>`,
    `<ul class="plain rows">\n${tools.map(t => toolRow(t, true)).join("\n")}\n</ul>`,
    vids.length ? `<h2 class="vsub">Our videos about ${esc(cat)}</h2>\n${grid(vids.slice(0, CAT_TOP))}` : "",
    vids.length ? `<p class="more-videos">Want more? <a href="/#videos-${slugOf(cat)}">All ${esc(plural(vids.length, "video"))} about ${esc(cat)} ›</a></p>` : "",
    newsletterBox()
  ].filter(Boolean).join("\n");
  out.set(p + "index.html", layout({
    path: p, nav: "tools", cls: "page",
    title: `${cat}: ${plural(tools.length, "tool")}${vids.length ? " and " + plural(vids.length, "video tutorial") : ""} | Use & Like`,
    description: `${cat} on Use & Like: ${nameList}.` + (vids.length ? ` ${plural(vids.length, "video tutorial")} from our channels.` : ""),
    noindex: !catIndexed(cat),
    jsonld: [crumbsLd([HOME, { name: cat, path: p }]), { "@context": "https://schema.org", "@type": "ItemList", name: cat,
      itemListElement: tools.map((t, i) => ({ "@type": "ListItem", position: i + 1, name: t.name, url: SITE + "/" + toolPath(t) })) }],
    main
  }));
  if (catIndexed(cat)) sitemap.push(p);
}

for (const t of TOOLS) {
  const vids = toolVideos.get(t.name), p = toolPath(t), cp = catPath(t.category);
  const others = toolsIn(t.category).filter(x => x !== t);
  const trail = [HOME, { name: t.category, path: cp }, { name: t.name, path: p }];
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
    path: p, nav: "tools", cls: "page",
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
const homeList = '<div class="index">\n' + CATEGORIES.map(cat => {
  const tools = toolsIn(cat);
  const items = !tools.length ? ['<li class="soon">Coming soon</li>'] : tools.slice(0, VISIBLE_COUNT)
    .map(t => `<li><a href="/${t.slug}" ${sponsored}>${esc(t.name)}</a></li>`);
  if (tools.length > VISIBLE_COUNT) items.push(`<li><a class="all" href="/${catPath(cat)}">All ${tools.length} ›</a></li>`);
  return `<section class="block"><h2><a href="/${catPath(cat)}">${esc(cat)}</a></h2><ul class="plain">${items.join("")}</ul></section>`;
}).join("\n") + "\n</div>";
function replaceBlock(html, name, content) {
  const re = new RegExp(`(<!-- build-pages:${name} -->)[\\s\\S]*?(<!-- /build-pages:${name} -->)`);
  if (!re.test(html)) throw new Error(`index.html has no <!-- build-pages:${name} --> markers`);
  return html.replace(re, (m, a, b) => `${a}\n${content}\n${b}`);
}
let newIndex = replaceBlock(indexHtml, "ld", ld(siteLd));
newIndex = replaceBlock(newIndex, "home", homeList);
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
for (const dir of ["tool", "category"]) {
  const base = path.join(ROOT, dir);
  if (!fs.existsSync(base)) continue;
  for (const name of fs.readdirSync(base)) {
    if (out.has(`${dir}/${name}/index.html`)) continue;
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
    `${TOOLS.length} tool pages, ${PAGES.length} other pages; ${indexed} pages in the sitemap ` +
    `(noindex for now: ${TOOLS.filter(t => !toolIndexed(t)).map(t => t.name).concat(CATEGORIES.filter(c => !catIndexed(c))).join(", ") || "none"}).`);
}
