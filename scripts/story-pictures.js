#!/usr/bin/env node
// Story pictures (Kevin, 2 Nov 2026, on the examples: "the story designs are also fire, that's how it should also look
// on the website"). For every story in data/news/ it renders, into img/stories/:
//   <slug>.jpg        1200x630  the share picture: what WhatsApp, X, Facebook, Telegram, Reddit and LinkedIn show when
//                               someone shares the story, and the large picture Google Discover can show (og:image)
//   <slug>-art.jpg    1200x600  the same look without words: the story page's picture and the front page lead
//   <slug>-thumb.jpg   320x160  the small picture in story lists
// plus img/share/default.jpg, the share picture of every other page. A story with a picture of its own ("image")
// keeps it on the page; the share picture is made for it anyway.
// Look: the app's icon(s) on its colour inside our royal blue, the tag, the headline (share picture only), our mark.
// Only stories whose words, tag, apps or icons changed are drawn again (data/story-pictures.json keeps a fingerprint);
// pictures of deleted stories are removed.
//
//   node scripts/story-pictures.js          (the daily news run: after the stories and app-icons.py, before build-pages.js)
//   node scripts/story-pictures.js --all    (draw everything again, e.g. after changing the design)
//
// Needs Playwright with Chromium (preinstalled in the cloud sessions) and the fonts Gelasio and Inter: read from
// ../useandlike-ops/analysis/newsletter/cards/.fonts or ~/.cache/useandlike-fonts, else downloaded once from Google Fonts.
"use strict";
const fs = require("fs"), path = require("path"), os = require("os"), crypto = require("crypto"), https = require("https");

const ROOT = path.join(__dirname, "..");
const NEWS = path.join(ROOT, "data", "news");
const OUT = path.join(ROOT, "img", "stories");
const STATE = path.join(ROOT, "data", "story-pictures.json");
const DESIGN = "3";                        // bump to draw every picture again after a design change
// 2 (Kevin, 2 Nov: "the logos seem smaller than they should be", then picked option B "same box, logo 2x bigger"):
// the logo fills about 64% of the story picture's height and 80% of the small list picture's height (was 50%).
// 3 (Kevin, 2 Nov: "the story below with the app logo can be 10% bigger"): the list picture's logo 480 -> 528 (88% of
// its height); two logos stay at 486 so the second one isn't cut off at the bottom.
const ART_ICON = 384, THUMB_ICON = 528, THUMB_TWO = 486;   // in the 1200x600 drawing; the list picture is that drawing at 320x160
const ICONS = JSON.parse(fs.readFileSync(path.join(ROOT, "data", "app-icons.json"), "utf8"));
const FONT_FILES = { "Gelasio-700.ttf": ["Gelasio", "0,700"], "Gelasio-600italic.ttf": ["Gelasio", "1,600"],
  "Inter-600.ttf": ["Inter", "0,600"], "Inter-700.ttf": ["Inter", "0,700"], "Inter-800.ttf": ["Inter", "0,800"] };
// Tag colours on the pictures (light pill, dark text).
const TAG = { "In testing": ["#ffcf5a", "#3a2a00"], Safety: ["#ff8a80", "#3d0a07"], "Heads-up": ["#ffd27a", "#3a2600"],
  Update: ["#9cc2ff", "#0b2350"], Offer: ["#8be3b0", "#073b22"], "New app": ["#d6b4ff", "#2c0f52"], "Big news": ["#ffffff", "#0f2a66"] };
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

function get(url, ua) {
  return new Promise((resolve, reject) => https.get(url, { headers: { "User-Agent": ua || "useandlike" } }, r => {
    if (r.statusCode >= 300 && r.statusCode < 400 && r.headers.location) return resolve(get(r.headers.location, ua));
    if (r.statusCode !== 200) return reject(new Error(url + ": " + r.statusCode));
    const chunks = []; r.on("data", c => chunks.push(c)); r.on("end", () => resolve(Buffer.concat(chunks)));
  }).on("error", reject));
}

async function fontsDir() {
  const dirs = [process.env.USEANDLIKE_FONTS, path.join(ROOT, "..", "useandlike-ops", "analysis", "newsletter", "cards", ".fonts"),
    path.join(os.homedir(), ".cache", "useandlike-fonts")].filter(Boolean);
  for (const d of dirs) if (Object.keys(FONT_FILES).every(f => fs.existsSync(path.join(d, f)))) return d;
  const d = dirs[dirs.length - 1];
  fs.mkdirSync(d, { recursive: true });
  for (const [file, [fam, axis]] of Object.entries(FONT_FILES)) {
    if (fs.existsSync(path.join(d, file))) continue;
    // An old user agent gets plain TTF files instead of WOFF2.
    const css = (await get(`https://fonts.googleapis.com/css2?family=${fam}:ital,wght@${axis}`, "Wget/1.21")).toString();
    const m = css.match(/url\((https:[^)]+)\)/);
    if (!m) throw new Error("No font file for " + file);
    fs.writeFileSync(path.join(d, file), await get(m[1]));
  }
  return d;
}

function fontCss(dir) {
  const face = (fam, file, w, style) => `@font-face{font-family:'${fam}';src:url('file://${path.join(dir, file)}');font-weight:${w};font-style:${style || "normal"}}`;
  return face("Gelasio", "Gelasio-700.ttf", 700) + face("Gelasio", "Gelasio-600italic.ttf", 600, "italic") +
    face("Inter", "Inter-600.ttf", 600) + face("Inter", "Inter-700.ttf", 700) + face("Inter", "Inter-800.ttf", 800);
}

function iconsOf(s) {
  const out = [];
  for (const a of (s.apps || []).filter(a => typeof a === "string")) {
    const e = ICONS[a];
    if (e && e.file && fs.existsSync(path.join(ROOT, e.file)) && !out.some(x => x.file === e.file)) out.push(e);
  }
  return out.slice(0, 2);
}

function fingerprint(s) {
  const icons = iconsOf(s).map(e => e.file + "@" + (e.v || ""));
  return crypto.createHash("sha1").update(JSON.stringify([DESIGN, s.head, s.tag || "", !!s.rumor, s.apps || [], icons])).digest("hex").slice(0, 8);
}

const dataUri = file => "data:image/webp;base64," + fs.readFileSync(path.join(ROOT, file)).toString("base64");
const MARK = size => `<svg width="${size}" height="${size}" viewBox="0 0 46 46"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#fff1b8"/><stop offset=".5" stop-color="#f6cf5a"/><stop offset="1" stop-color="#d9a22a"/></linearGradient></defs>
  <rect width="46" height="46" rx="10" fill="#1a46a6"/><rect x="3.6" y="3.6" width="38.8" height="38.8" rx="7.4" fill="none" stroke="url(#g)" stroke-width="1.6"/>
  <text x="23" y="33" text-anchor="middle" font-family="Gelasio" font-style="italic" font-weight="600" font-size="27" fill="#fff">&amp;</text></svg>`;

function ground(w, h, cx, cy, color, seed) {
  // Royal blue with the app's colour as a glow behind the icon, glassy app tiles towards the edges and a few sparkles.
  let n = seed, tiles = "", sparks = "";
  const rnd = () => (n = (n * 16807) % 2147483647) / 2147483647;
  for (let y = -30; y < h; y += 116) for (let x = -30; x < w; x += 116) {
    const d = Math.hypot((x + 48 - cx) / w, (y + 48 - cy) / h);
    const a = Math.max(0, Math.min(1, (d - 0.42) / 0.4));
    if (a > 0.05 && rnd() > 0.3)
      tiles += `<rect x="${x}" y="${y}" width="94" height="94" rx="21" fill="rgba(255,255,255,${(0.06 * a).toFixed(3)})" stroke="rgba(220,230,245,${(0.22 * a).toFixed(3)})" stroke-width="2"/>`;
  }
  for (let i = 0; i < 26; i++)
    sparks += `<circle cx="${(rnd() * w).toFixed(0)}" cy="${(rnd() * h).toFixed(0)}" r="${(1.2 + rnd() * 2.6).toFixed(1)}" fill="rgba(255,248,220,${(0.25 + rnd() * 0.5).toFixed(2)})"/>`;
  return `<div style="position:absolute;inset:0;background:radial-gradient(circle at ${cx}px ${cy}px, ${color} 0%, ${color}cc 20%, #1a46a6 52%, #0f2a66 100%)"></div>
    <div style="position:absolute;inset:0;background:radial-gradient(circle at ${cx}px ${cy}px, rgba(255,255,255,.26), rgba(255,255,255,0) 34%)"></div>
    <svg width="${w}" height="${h}" style="position:absolute;inset:0">${tiles}${sparks}</svg>`;
}

function iconBlock(icons, s, cx, cy, big) {
  const shadow = "box-shadow:0 22px 50px rgba(0,0,30,.38)";
  if (!icons.length) {
    const letter = esc(((s.apps || [])[0] || s.head || "?")[0]);
    return `<div style="position:absolute;left:${cx - big / 2}px;top:${cy - big / 2}px;width:${big}px;height:${big}px;border-radius:${big * 0.23}px;
      background:#fff;display:grid;place-items:center;font:700 ${big * 0.55}px/1 Gelasio;color:#1a46a6;${shadow}">${letter}</div>`;
  }
  if (icons.length === 1)
    return `<img src="${dataUri(icons[0].file)}" style="position:absolute;left:${cx - big / 2}px;top:${cy - big / 2}px;width:${big}px;height:${big}px;border-radius:${big * 0.23}px;${shadow}">`;
  const a = big * 0.84, b = big * 0.58;
  return `<img src="${dataUri(icons[0].file)}" style="position:absolute;left:${cx - a * 0.72}px;top:${cy - a * 0.62}px;width:${a}px;height:${a}px;border-radius:${a * 0.23}px;${shadow}">
    <img src="${dataUri(icons[1].file)}" style="position:absolute;left:${cx + a * 0.02}px;top:${cy + a * 0.02}px;width:${b}px;height:${b}px;border-radius:${b * 0.23}px;border:6px solid #fff;${shadow}">`;
}

function sharePage(s, seed) {
  const icons = iconsOf(s), color = (icons[0] && icons[0].color) || "#2c63d8";
  const tag = s.tag || (s.rumor ? "In testing" : ""), [bg, fg] = TAG[tag] || ["#dfe6ef", "#0f2a66"];
  return `<div style="position:relative;width:1200px;height:630px;overflow:hidden">${ground(1200, 630, 225, 315, color, seed)}
    ${iconBlock(icons, s, 225, 315, 300)}
    <div style="position:absolute;left:470px;top:60px;right:56px;bottom:120px;display:flex;flex-direction:column;justify-content:center;gap:24px">
      ${tag ? `<span style="align-self:flex-start;font:800 24px/1 Inter;letter-spacing:2px;text-transform:uppercase;color:${fg};background:${bg};padding:12px 18px;border-radius:999px">${esc(tag)}</span>` : ""}
      <div style="font:700 ${s.head.length > 70 ? 48 : 56}px/1.12 Gelasio;font-variant-numeric:lining-nums;color:#fff;text-wrap:balance;text-shadow:0 3px 14px rgba(0,0,30,.35)">${esc(s.head)}</div>
    </div>
    <div style="position:absolute;left:470px;bottom:46px;display:flex;align-items:center;gap:14px">${MARK(54)}
      <span style="font:700 26px/1 Inter;color:#fff">Use <span style="color:#f6cf5a">&amp;</span> Like</span>
      <span style="font:600 22px/1 Inter;color:#cfd8e6;margin-left:10px">useandlike.com</span></div></div>`;
}

function artPage(s, seed, scale, big) {
  const icons = iconsOf(s), color = (icons[0] && icons[0].color) || "#2c63d8";
  return `<div style="width:${1200 * scale}px;height:${600 * scale}px;overflow:hidden"><div style="position:relative;width:1200px;height:600px;overflow:hidden;transform:scale(${scale});transform-origin:0 0">
    ${ground(1200, 600, 600, 300, color, seed)}${iconBlock(icons, s, 600, 300, big)}</div></div>`;
}

function defaultPage(seed) {
  return `<div style="position:relative;width:1200px;height:630px;overflow:hidden">${ground(1200, 630, 600, 315, "#2c63d8", seed)}
    <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px">${MARK(150)}
      <div style="font:700 110px/1 Gelasio;color:#fff;letter-spacing:-1px">Use <span style="font:600 italic 110px/1 Gelasio;color:#f6cf5a">&amp;</span> Like</div>
      <div style="font:800 34px/1 Inter;letter-spacing:5px;text-transform:uppercase;color:#dfe6ef">App news, deals and how-tos</div>
      <div style="font:700 28px/1 Inter;color:#fff;padding:12px 24px;border:3px solid #f2c14e;border-radius:999px">useandlike.com</div></div></div>`;
}

(async () => {
  const all = process.argv.includes("--all");
  const stories = fs.readdirSync(NEWS).filter(f => f.endsWith(".json")).map(f => JSON.parse(fs.readFileSync(path.join(NEWS, f), "utf8")));
  const state = fs.existsSync(STATE) ? JSON.parse(fs.readFileSync(STATE, "utf8")) : {};
  const done = state.stories || {};
  fs.mkdirSync(OUT, { recursive: true });
  fs.mkdirSync(path.join(ROOT, "img", "share"), { recursive: true });
  const todo = stories.filter(s => all || done[s.slug] !== fingerprint(s) ||
    !["", "-art", "-thumb"].every(k => fs.existsSync(path.join(OUT, s.slug + k + ".jpg"))));
  const needDefault = all || state.design !== DESIGN || !fs.existsSync(path.join(ROOT, "img", "share", "default.jpg"));
  const keep = new Set(stories.map(s => s.slug));
  let removed = 0;
  for (const f of fs.readdirSync(OUT)) {
    const slug = f.replace(/(-art|-thumb)?\.jpg$/, "");
    if (!keep.has(slug)) { fs.unlinkSync(path.join(OUT, f)); removed++; }
  }
  for (const k of Object.keys(done)) if (!keep.has(k)) delete done[k];
  if (todo.length || needDefault) {
    const { chromium } = require("playwright");
    const css = fontCss(await fontsDir());
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "story-pics-"));
    const browser = await chromium.launch();
    const page = await browser.newPage();
    const shot = async (html, w, h, file) => {
      // A file page (not setContent) so the file:// fonts load.
      const f = path.join(tmp, "p.html");
      fs.writeFileSync(f, `<!doctype html><meta charset="utf-8"><style>${css}*{margin:0;box-sizing:border-box}body{background:#0f2a66}</style>${html}`);
      await page.setViewportSize({ width: w, height: h });
      await page.goto("file://" + f);
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: file, type: "jpeg", quality: 84 });
    };
    for (const s of todo) {
      const seed = parseInt(fingerprint(s).slice(0, 6), 16) % 2147483646 + 1;
      await shot(sharePage(s, seed), 1200, 630, path.join(OUT, s.slug + ".jpg"));
      await shot(artPage(s, seed, 1, ART_ICON), 1200, 600, path.join(OUT, s.slug + "-art.jpg"));
      await shot(artPage(s, seed, 320 / 1200, iconsOf(s).length > 1 ? THUMB_TWO : THUMB_ICON), 320, 160, path.join(OUT, s.slug + "-thumb.jpg"));
      done[s.slug] = fingerprint(s);
    }
    if (needDefault) await shot(defaultPage(4242), 1200, 630, path.join(ROOT, "img", "share", "default.jpg"));
    await browser.close();
  }
  fs.writeFileSync(STATE, JSON.stringify({ _about: "Written by scripts/story-pictures.js: a fingerprint per story of what its pictures in " +
    "img/stories/ show (words, tag, apps, icons). build-pages.js adds it to the picture links so changed pictures load fresh.",
    design: DESIGN, stories: Object.fromEntries(Object.entries(done).sort()) }, null, 1) + "\n");
  console.log(`Story pictures: ${todo.length} drawn, ${stories.length - todo.length} unchanged, ${removed} old files removed` +
    (needDefault ? "; default share picture drawn." : "."));
})().catch(e => { console.error("Story pictures failed: " + e.message); process.exit(1); });
