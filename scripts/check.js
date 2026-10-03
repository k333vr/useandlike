// Checks index.html after edits. Run: node scripts/check.js [--online]
//   --online  also visits every affiliate link to confirm it responds.
// Needs Playwright (preinstalled in Claude Code cloud sessions).
const path = require("path");
const fs = require("fs");
const { execSync } = require("child_process");

function loadPlaywright() {
  try { return require("playwright"); } catch (_) {}
  const root = execSync("npm root -g").toString().trim();
  return require(path.join(root, "playwright"));
}

const ONLINE = process.argv.includes("--online");
const FILE = "file://" + path.resolve(__dirname, "..", "index.html");
const BANNED = /\b(best|cheapest|fastest|#1|number one|top-rated|unbeatable|perfect)\b/i;

// Read _redirects: "/slug  https://target  302" per line.
function readRedirects(errors, warnings) {
  const map = new Map();
  const file = path.resolve(__dirname, "..", "_redirects");
  if (!fs.existsSync(file)) { errors.push("_redirects file is missing"); return map; }
  fs.readFileSync(file, "utf8").split("\n").forEach((raw, i) => {
    const line = raw.trim();
    if (!line || line.startsWith("#")) return;
    const where = `_redirects line ${i + 1}`;
    const [from, to, code, extra] = line.split(/\s+/);
    if (extra || !to) return errors.push(`${where}: expected "/short-name  https://link  302"`);
    if (!/^\/[a-z0-9-]+$/.test(from)) return errors.push(`${where}: short name "${from}" should be lowercase letters, numbers, dashes`);
    if (code !== "302") errors.push(`${where}: use 302 so updated links aren't cached by browsers`);
    try { if (new URL(to).protocol !== "https:") warnings.push(`${where}: link is not https`); }
    catch (_) { errors.push(`${where}: not a valid link: ${to}`); }
    const slug = from.slice(1);
    if (map.has(slug)) errors.push(`${where}: /${slug} is listed twice`);
    if (/^(index|scripts|readme|claude)/i.test(slug)) errors.push(`${where}: /${slug} clashes with a site file`);
    map.set(slug, to);
  });
  return map;
}

(async () => {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const errors = [], warnings = [];
  const redirects = readRedirects(errors, warnings);

  for (const scheme of ["light", "dark"]) {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, colorScheme: scheme });
    page.on("pageerror", e => errors.push(`[${scheme}] page error: ${e.message}`));
    page.on("console", m => m.type() === "error" && errors.push(`[${scheme}] console: ${m.text()}`));
    await page.goto(FILE);

    if (scheme === "light") {
      const data = await page.evaluate(() => ({ TOOLS, CATEGORIES, CHANNEL_SEARCH_URL, VISIBLE_COUNT, VIDEOS }));
      const names = new Set();
      for (const t of data.TOOLS) {
        const who = `"${t.name || "?"}"`;
        for (const k of ["name", "category", "description", "slug"])
          if (!t[k] || typeof t[k] !== "string") errors.push(`${who}: missing "${k}"`);
        if (names.has(t.name)) errors.push(`${who}: listed twice`);
        names.add(t.name);
        if (!data.CATEGORIES.includes(t.category)) errors.push(`${who}: category "${t.category}" is not in CATEGORIES`);
        if (!redirects.has(t.slug)) errors.push(`${who}: no line for /${t.slug} in _redirects`);
        else if (/example\.com/.test(redirects.get(t.slug))) warnings.push(`${who}: /${t.slug} is still a placeholder link`);
        for (const k of ["description", "why", "details"])
          if (BANNED.test(t[k] || "")) errors.push(`${who}: superlative in ${k}: "${t[k]}"`);
      }
      for (const c of data.CATEGORIES) {
        const tools = data.TOOLS.filter(t => t.category === c);
        const picks = tools.filter(t => t.isPick).length;
        if (!tools.length) warnings.push(`category "${c}" has no tools (shows "Coming soon")`);
        else if (picks > 1) errors.push(`category "${c}" has ${picks} "Our pick" tools, expected at most 1`);
        else if (!picks) console.log(`info category "${c}" has no "Our pick" yet`);
      }
      for (const v of data.VIDEOS) {
        const who = `video "${v.title || "?"}"`;
        for (const k of ["title", "url", "category"])
          if (!v[k] || typeof v[k] !== "string") errors.push(`${who}: missing "${k}"`);
        if (!data.CATEGORIES.includes(v.category)) errors.push(`${who}: category "${v.category}" is not in CATEGORIES`);
        if (v.tool && !names.has(v.tool)) errors.push(`${who}: tool "${v.tool}" is not in TOOLS (names must match exactly)`);
        if (v.tool && data.TOOLS.find(t => t.name === v.tool && t.category !== v.category))
          errors.push(`${who}: tool "${v.tool}" is in a different category`);
        try { if (!/(^|\.)(youtube\.com|youtu\.be)$/.test(new URL(v.url).hostname)) warnings.push(`${who}: link is not a YouTube link`); }
        catch (_) { errors.push(`${who}: not a valid link: ${v.url}`); }
      }
      const used = new Set(data.TOOLS.map(t => t.slug));
      for (const slug of redirects.keys())
        if (!used.has(slug)) console.log(`info /${slug} is a short link only (not listed on the page)`);
      if (/YOURCHANNEL/.test(data.CHANNEL_SEARCH_URL)) errors.push("CHANNEL_SEARCH_URL still contains YOURCHANNEL");
      if (data.CHANNEL_SEARCH_URL === "https://www.youtube.com/results?search_query=")
        warnings.push("CHANNEL_SEARCH_URL searches all of YouTube, not your channel");

      // Every category opens and shows its tools; every Visit link is marked sponsored.
      for (const c of data.CATEGORIES) {
        const id = c.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        await page.click(`#${id} .cat-toggle`);
        const shown = await page.$$eval(`#${id} .tool`, e => e.filter(x => x.offsetParent).length);
        const expected = Math.min(data.TOOLS.filter(t => t.category === c).length, data.VISIBLE_COUNT);
        if (shown !== expected) errors.push(`category "${c}": ${shown} tools visible, expected ${expected}`);
        if (await page.$(`#${id} .show-all`)) await page.click(`#${id} .show-all`);
      }
      const badRel = await page.$$eval("#view-tools a.btn, #view-tools a.tool-name", as => as.filter(a => !a.relList.contains("sponsored")).length);
      if (badRel) errors.push(`${badRel} affiliate link(s) missing rel="sponsored"`);
      const visits = await page.$$eval("#view-tools a.btn", as => as.length);
      if (visits !== data.TOOLS.length) errors.push(`${visits} Visit buttons for ${data.TOOLS.length} tools`);

      // "More" opens the details; the Videos tab lists every tool.
      const firstMore = await page.$("#view-tools .tool .more");
      if (firstMore) {
        await firstMore.click();
        if (!(await page.$eval("#view-tools .tool .more-body", e => !!e.offsetParent))) errors.push('"More" does not open the details');
      }
      await page.click("#tab-videos");
      for (const c of data.CATEGORIES) await page.click(`#videos-${c.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")} .cat-toggle`);
      const vtools = await page.$$eval("#view-videos .tool", e => e.length);
      if (vtools !== data.TOOLS.length) errors.push(`Videos tab lists ${vtools} tools, expected ${data.TOOLS.length}`);
      await page.fill("#q", data.TOOLS[0] ? data.TOOLS[0].name : "x");
      if (data.TOOLS[0] && !(await page.$$eval("#results .tool", e => e.length))) errors.push("search finds nothing for the first tool's name");
      await page.fill("#q", "");
      await page.click("#tab-tools");
      const tabs = await page.$$eval("a.btn", as => [...new Set(as.map(a => a.target === "_blank" ? "new" : "same"))]);
      console.log(`info links open in: ${tabs.join(", ")} tab`);
    }
    const width = await page.evaluate(() => document.documentElement.scrollWidth);
    if (width > 390) errors.push(`[${scheme}] page scrolls sideways on a phone (${width}px wide)`);
    await page.screenshot({ path: path.join(process.env.CHECK_OUT || require("os").tmpdir(), `useandlike-${scheme}.png`), fullPage: true });
    await page.close();
  }

  if (ONLINE) {
    const page = await browser.newPage();
    for (const [slug, url] of redirects) {
      if (/example\.com/.test(url)) continue;
      try {
        const res = await page.goto(url, { timeout: 20000, waitUntil: "domcontentloaded" });
        const status = res ? res.status() : 0;
        if (status >= 400) warnings.push(`/${slug}: link returned HTTP ${status} (${url})`);
        else console.log(`ok   /${slug} -> ${page.url()}`);
      } catch (e) { warnings.push(`/${slug}: link could not be opened (${e.message.split("\n")[0]})`); }
    }
  }

  await browser.close();
  warnings.forEach(w => console.log("WARN " + w));
  errors.forEach(e => console.log("FAIL " + e));
  console.log(errors.length ? `\n${errors.length} problem(s) found.` : `\nAll checks passed (${warnings.length} warning(s)).`);
  process.exit(errors.length ? 1 : 0);
})();
