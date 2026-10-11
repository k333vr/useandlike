// Checks the site after edits. Run: node scripts/check.js [--online]
//   --online  also visits every affiliate link to confirm it responds.
// Checks index.html and the pages made by scripts/build-pages.js (category and tool pages, about pages, sitemap),
// served from this folder by a small local server. Needs Playwright (preinstalled in Claude Code cloud sessions).
const path = require("path");
const fs = require("fs");
const http = require("http");
const { execSync, spawnSync } = require("child_process");

function loadPlaywright() {
  try { return require("playwright"); } catch (_) {}
  const root = execSync("npm root -g").toString().trim();
  return require(path.join(root, "playwright"));
}

const ONLINE = process.argv.includes("--online");
const ROOT = path.resolve(__dirname, "..");
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".jpg": "image/jpeg",
  ".png": "image/png", ".webp": "image/webp", ".xml": "application/xml", ".txt": "text/plain" };
// Serves this folder like Cloudflare does: /category/email/ -> category/email/index.html (short links are not served).
function serve() {
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
      if (p.endsWith("/")) p += "index.html";
      const file = path.join(ROOT, p);
      if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end("Not found"); }
      res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
      fs.createReadStream(file).pipe(res);
    }).listen(0, "127.0.0.1", () => resolve(server));
  });
}
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
    if (/^(index|scripts|readme|claude|category|tool|about|how-we-|work-with-us|sitemap|robots|thumbs|img|bh|videos)/i.test(slug))
      errors.push(`${where}: /${slug} clashes with a site file or page`);
    map.set(slug, to);
  });
  return map;
}

(async () => {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const errors = [], warnings = [];
  const redirects = readRedirects(errors, warnings);
  const server = await serve();
  const BASE = `http://127.0.0.1:${server.address().port}`;
  const FILE = BASE + "/";

  // The category and tool pages are made from index.html: they must match it.
  const built = spawnSync(process.execPath, [path.join(__dirname, "build-pages.js"), "--check"], { encoding: "utf8" });
  if (built.status !== 0) errors.push((built.stdout || built.stderr || "build-pages.js failed").trim());

  for (const scheme of ["light", "dark"]) {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, colorScheme: scheme });
    page.on("pageerror", e => errors.push(`[${scheme}] page error: ${e.message}`));
    page.on("console", m => m.type() === "error" && errors.push(`[${scheme}] console: ${m.text()}`));
    // Beehiiv's signup form is an outside service: not loaded here, so the check works offline too.
    await page.route("https://subscribe-forms.beehiiv.com/**", r => r.fulfill({ contentType: "text/javascript", body: "" }));
    await page.goto(FILE);

    if (scheme === "light") {
      const data = await page.evaluate(() => ({ TOOLS, CATEGORIES, CHANNELS, VISIBLE_COUNT, VIDEOS, NEWSLETTER }));
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
      if (data.NEWSLETTER.ready && !redirects.has("newsletter"))
        errors.push('NEWSLETTER.ready is true but _redirects has no "/newsletter" line');
      if (!data.CHANNELS.length) warnings.push("CHANNELS is empty, so the Videos tab has no channel links");
      for (const c of data.CHANNELS)
        if (!c.name || !/^@[A-Za-z0-9._-]+$/.test(c.handle || "")) errors.push(`channel "${c.name || "?"}": handle should look like "@ChannelName"`);

      const slugOf = c => c.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const isSponsored = sel => page.$$eval(sel, as => as.filter(a => !a.relList.contains("sponsored")).length);

      // Home: every category is listed with its first few tools as direct affiliate links.
      const blocks = await page.$$eval(".index .block", e => e.length);
      if (blocks !== data.CATEGORIES.length) errors.push(`home lists ${blocks} categories, expected ${data.CATEGORIES.length}`);
      const homeLinks = await page.$$eval('.index li a:not(.all)', e => e.length);
      const expectedHome = data.CATEGORIES.reduce((n, c) => n + Math.min(data.TOOLS.filter(t => t.category === c).length, data.VISIBLE_COUNT), 0);
      if (homeLinks !== expectedHome) errors.push(`home shows ${homeLinks} tool links, expected ${expectedHome}`);
      if (await isSponsored(".index li a:not(.all)")) errors.push('home tool links missing rel="sponsored"');

      // Home: category headings open the real category pages; the back button returns to the list.
      const catHrefs = await page.$$eval(".index .block h2 a", as => as.map(a => a.getAttribute("href")));
      const expectHrefs = data.CATEGORIES.map(c => `/category/${slugOf(c)}/`);
      if (catHrefs.join() !== expectHrefs.join()) errors.push("home category links don't point at /category/<name>/ pages");
      await page.click(`.index .block h2 a[href="${expectHrefs[0]}"]`);
      await page.waitForURL("**" + expectHrefs[0], { timeout: 5000 }).catch(() => errors.push("home: category link does not open its page"));
      await page.goBack();
      await page.waitForSelector(".index", { timeout: 3000 }).catch(() => {});
      if (!(await page.$(".index"))) { errors.push("back button does not return to the category list"); await page.goto(FILE); }

      // Old "#" links (YouTube descriptions) forward to the real pages.
      for (const [hash, to] of data.CATEGORIES.map(c => [slugOf(c), `/category/${slugOf(c)}/`]).concat([["about", "/about/"]])) {
        await page.goto(FILE + "#" + hash);
        await page.waitForURL("**" + to, { timeout: 5000 }).catch(() => {});
        if (page.url() !== BASE + to) errors.push(`useandlike.com/#${hash} does not forward to ${to}`);
      }

      // Each category page: all its tools with Visit buttons; each tool page: a Visit button to its short link.
      const pageCheck = async (p, label) => {
        const res = await page.goto(BASE + p);
        if (!res || res.status() !== 200) { errors.push(`${label}: page missing (run node scripts/build-pages.js)`); return null; }
        if (await page.$eval('link[rel="canonical"]', l => l.href).catch(() => "") !== "https://useandlike.com" + p)
          errors.push(`${label}: canonical link should be https://useandlike.com${p}`);
        const width = await page.evaluate(() => document.documentElement.scrollWidth);
        if (width > 390) errors.push(`${label} scrolls sideways on a phone (${width}px wide)`);
        const text = await page.evaluate(() => [document.title, (document.querySelector('meta[name="description"]') || {}).content || "",
          ...[...document.querySelectorAll("main h1, main .lead, main .desc, main .note, main .checks li, main.info p")].map(e => e.textContent)].join(" | "));
        const bad = text.match(BANNED);
        if (bad) errors.push(`${label}: superlative "${bad[0]}" in the page text`);
        return page;
      };
      for (const c of data.CATEGORIES) {
        const p = `/category/${slugOf(c)}/`;
        if (!(await pageCheck(p, `category page "${c}"`))) continue;
        const rows = await page.$$eval(".row", e => e.length);
        const expected = data.TOOLS.filter(t => t.category === c).length;
        if (rows !== expected) errors.push(`category page "${c}": ${rows} tools, expected ${expected}`);
        if (await isSponsored(".row a.name, .row a.visit")) errors.push(`category page "${c}": affiliate link missing rel="sponsored"`);
      }
      const noindex = new Set();
      for (const t of data.TOOLS) {
        const p = `/tool/${t.slug}/`;
        if (!(await pageCheck(p, `tool page "${t.name}"`))) continue;
        const visit = await page.$$eval("a.visit", as => as.map(a => ({ href: a.getAttribute("href"), sponsored: a.relList.contains("sponsored") })));
        if (!visit.length || visit.some(v => v.href !== "/" + t.slug || !v.sponsored))
          errors.push(`tool page "${t.name}": Visit button should go to /${t.slug} with rel="sponsored"`);
        if (await page.$('meta[name="robots"][content*="noindex"]')) noindex.add(p);
      }
      for (const p of ["/about/", "/how-we-choose/", "/how-we-make-money/", "/work-with-us/"]) await pageCheck(p, `page ${p}`);

      // The sitemap lists the pages search engines should show (not the "noindex" ones), and they exist.
      const sitemap = fs.existsSync(path.join(ROOT, "sitemap.xml")) ? fs.readFileSync(path.join(ROOT, "sitemap.xml"), "utf8") : "";
      const listed = [...sitemap.matchAll(/<loc>https:\/\/useandlike\.com(\/[^<]*)<\/loc>/g)].map(m => m[1]);
      if (!listed.length) errors.push("sitemap.xml is missing or empty (run node scripts/build-pages.js)");
      for (const p of listed) {
        if (noindex.has(p)) errors.push(`sitemap.xml lists ${p}, which is marked noindex`);
        if (!fs.existsSync(path.join(ROOT, p, "index.html")) && p !== "/") errors.push(`sitemap.xml lists ${p}, which doesn't exist`);
      }
      console.log(`info ${listed.length} pages in the sitemap; ${noindex.size} tool pages wait for more content (noindex)`);
      await page.goto(FILE);

      // Videos tab: a button per category plus "All"; videos.js loads, cards page in with "Show more".
      await page.click("#nav-videos");
      await page.waitForFunction(() => location.hash === "#videos");
      await page.waitForFunction(() => window.CHANNEL_VIDEOS && !document.querySelector(".loading"), null, { timeout: 15000 }).catch(() => {});
      const vdata = await page.evaluate(() => ({ n: (window.CHANNEL_VIDEOS || []).length, tools: window.CHANNEL_VIDEO_TOOLS || [], ids: (window.CHANNEL_VIDEOS || []).map(r => r[0]), used: [...new Set((window.CHANNEL_VIDEOS || []).map(r => window.CHANNEL_VIDEO_TOOLS[r[3]]))] }));
      if (!vdata.n) errors.push("videos.js did not load (run python3 scripts/build-videos.py)");
      const toolNames = new Set(data.TOOLS.map(t => t.name));
      for (const t of vdata.tools) if (!toolNames.has(t)) warnings.push(`videos.js lists videos for "${t}", which is no longer in TOOLS (re-run scripts/build-videos.py)`);
      const total = data.VIDEOS.length + vdata.n;
      const chips = await page.$$eval(".chips .chip", e => e.length);
      if (chips !== data.CATEGORIES.length + 1) errors.push(`Videos tab has ${chips} category buttons, expected ${data.CATEGORIES.length + 1}`);
      const cards = await page.$$eval(".vgrid .vcard", e => e.length);
      if (cards !== Math.min(24, total)) errors.push(`Videos tab shows ${cards} videos at first, expected ${Math.min(24, total)}`);
      const allShown = await page.evaluate(() => { const b = document.querySelector("button.more"); let i = 0;
        while (b && !b.classList.contains("hidden") && i++ < 1000) b.click(); return document.querySelectorAll(".vgrid .vcard").length; });
      if (allShown !== total) errors.push(`"Show more" reaches ${allShown} videos, expected ${total}`);
      for (const v of data.VIDEOS) {
        const id = (v.url.match(/[?&]v=([\w-]{11})$/) || [])[1];
        if (!id) errors.push(`video "${v.title}": URL should end in ?v= and an 11-character video ID`);
        else if (!fs.existsSync(path.resolve(__dirname, "..", "thumbs", id + ".jpg"))) warnings.push(`video "${v.title}": no thumbnail at thumbs/${id}.jpg`);
      }
      const noThumb = vdata.ids.filter(id => !fs.existsSync(path.resolve(__dirname, "..", "thumbs", id + ".jpg")));
      if (noThumb.length) warnings.push(`${noThumb.length} channel videos have no thumbnail yet (run python3 scripts/build-videos.py)`);
      let catTotal = 0, searchRows = 0;
      for (const c of data.CATEGORIES) {
        await page.goto(FILE + "#videos-" + slugOf(c));
        await page.waitForFunction(() => !document.querySelector(".loading"), null, { timeout: 8000 }).catch(() => {});
        catTotal += await page.evaluate(() => { const b = document.querySelector("button.more"); let i = 0;
          while (b && !b.classList.contains("hidden") && i++ < 1000) b.click(); return document.querySelectorAll(".vgrid .vcard").length; });
        searchRows += await page.$$eval(".vrow", e => e.length);
      }
      if (catTotal !== total) errors.push(`category video pages show ${catTotal} videos, expected ${total}`);
      const withVideos = new Set(data.VIDEOS.map(v => v.tool).filter(Boolean).concat(vdata.used));
      const expectSearch = data.TOOLS.filter(t => !withVideos.has(t.name)).length;
      if (searchRows !== expectSearch) errors.push(`${searchRows} tools offer channel search, expected ${expectSearch}`);
      await page.goto(BASE + "/category/" + slugOf(data.CATEGORIES[0]) + "/");
      const tabs = await page.$$eval("a.visit", as => [...new Set(as.map(a => a.target === "_blank" ? "new" : "same"))]);
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
  server.close();
  warnings.forEach(w => console.log("WARN " + w));
  errors.forEach(e => console.log("FAIL " + e));
  console.log(errors.length ? `\n${errors.length} problem(s) found.` : `\nAll checks passed (${warnings.length} warning(s)).`);
  process.exit(errors.length ? 1 : 0);
})();
