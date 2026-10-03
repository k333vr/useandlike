// Checks index.html after edits. Run: node scripts/check.js [--online]
//   --online  also visits every affiliate link to confirm it responds.
// Needs Playwright (preinstalled in Claude Code cloud sessions).
const path = require("path");
const { execSync } = require("child_process");

function loadPlaywright() {
  try { return require("playwright"); } catch (_) {}
  const root = execSync("npm root -g").toString().trim();
  return require(path.join(root, "playwright"));
}

const ONLINE = process.argv.includes("--online");
const FILE = "file://" + path.resolve(__dirname, "..", "index.html");
const BANNED = /\b(best|cheapest|fastest|#1|number one|top-rated|unbeatable|perfect)\b/i;

(async () => {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const errors = [], warnings = [];
  let allTools = [];

  for (const scheme of ["light", "dark"]) {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, colorScheme: scheme });
    page.on("pageerror", e => errors.push(`[${scheme}] page error: ${e.message}`));
    page.on("console", m => m.type() === "error" && errors.push(`[${scheme}] console: ${m.text()}`));
    await page.goto(FILE);

    if (scheme === "light") {
      const data = await page.evaluate(() => ({ TOOLS, CATEGORIES, CHANNEL_SEARCH_URL, VISIBLE_COUNT }));
      allTools = data.TOOLS;
      const names = new Set();
      for (const t of data.TOOLS) {
        const who = `"${t.name || "?"}"`;
        for (const k of ["name", "category", "description", "why", "url"])
          if (!t[k] || typeof t[k] !== "string") errors.push(`${who}: missing "${k}"`);
        if (names.has(t.name)) errors.push(`${who}: listed twice`);
        names.add(t.name);
        if (!data.CATEGORIES.includes(t.category)) errors.push(`${who}: category "${t.category}" is not in CATEGORIES`);
        try { const u = new URL(t.url); if (u.protocol !== "https:") warnings.push(`${who}: link is not https`); }
        catch (_) { errors.push(`${who}: link is not a valid URL: ${t.url}`); }
        if (/example\.com/.test(t.url)) warnings.push(`${who}: still a placeholder link`);
        for (const k of ["description", "why"])
          if (BANNED.test(t[k] || "")) errors.push(`${who}: superlative in ${k}: "${t[k]}"`);
      }
      for (const c of data.CATEGORIES) {
        const tools = data.TOOLS.filter(t => t.category === c);
        const picks = tools.filter(t => t.isPick).length;
        if (!tools.length) warnings.push(`category "${c}" has no tools (shows "Coming soon")`);
        else if (picks !== 1) errors.push(`category "${c}" has ${picks} "Our pick" tools, expected 1`);
      }
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
      const badRel = await page.$$eval("a.btn-primary", as => as.filter(a => a.rel !== "sponsored noopener" || a.target !== "_blank").length);
      if (badRel) errors.push(`${badRel} Visit link(s) missing rel="sponsored noopener" / target="_blank"`);
    }
    const width = await page.evaluate(() => document.documentElement.scrollWidth);
    if (width > 390) errors.push(`[${scheme}] page scrolls sideways on a phone (${width}px wide)`);
    await page.screenshot({ path: path.join(process.env.CHECK_OUT || require("os").tmpdir(), `useandlike-${scheme}.png`), fullPage: true });
    await page.close();
  }

  if (ONLINE) {
    const page = await browser.newPage();
    for (const t of allTools) {
      if (/example\.com/.test(t.url)) continue;
      try {
        const res = await page.goto(t.url, { timeout: 20000, waitUntil: "domcontentloaded" });
        const status = res ? res.status() : 0;
        if (status >= 400) warnings.push(`"${t.name}": link returned HTTP ${status} (${t.url})`);
        else console.log(`ok   ${t.name} -> ${page.url()}`);
      } catch (e) { warnings.push(`"${t.name}": link could not be opened (${e.message.split("\n")[0]})`); }
    }
  }

  await browser.close();
  warnings.forEach(w => console.log("WARN " + w));
  errors.forEach(e => console.log("FAIL " + e));
  console.log(errors.length ? `\n${errors.length} problem(s) found.` : `\nAll checks passed (${warnings.length} warning(s)).`);
  process.exit(errors.length ? 1 : 0);
})();
