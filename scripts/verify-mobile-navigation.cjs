const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');

async function verifyTags(page, base) {
  await page.goto(new URL('/tags/', base).href);
  const input = page.locator('[data-tag-filter]');
  const status = page.locator('[data-tag-status]');
  const links = page.locator('.taxonomy li:visible a');
  const play = links.filter({ hasText: 'Playwright' });
  await input.fill('Playwright');
  const matches = await links.allTextContents();
  const count = await status.textContent();
  assert.ok(matches.length && matches.every(text => text.toLowerCase().includes('playwright')));
  await play.first().tap();
  await page.waitForURL(url => url.pathname !== '/tags/');
  await page.evaluate(() => { setTimeout(() => history.back(), 0); });
  await page.waitForFunction(expected => document.querySelector('[data-tag-status]')?.textContent === expected, count);
  assert.equal(await input.inputValue(), 'Playwright');
  assert.deepEqual(await links.allTextContents(), matches);
  await input.fill('nonexistent-tag-0a9f');
  assert.equal(await links.count(), 0);
  assert.equal(await page.locator('.tag-library details').isVisible(), false);
  await input.fill('');
  assert.ok(await links.count() > matches.length);
  return page.evaluate(() => window.tagCacheRestore);
}

async function verifyCategoryTree(page, base) {
  await page.goto(new URL('/categories/', base).href);
  await page.locator('.catalog-menu > summary').tap();
  const branch = page.locator('.catalog-menu nav details').filter({
    has: page.locator(':scope > summary', { hasText: '自动化测试' }),
  });
  await branch.locator(':scope > summary').tap();
  assert.ok(await branch.evaluate(details => details.open));
  const layout = await page.locator('.catalog-menu nav > ul').evaluate(tree => {
    const expanded = tree.querySelector(':scope > li:has(> details[open])');
    const counts = [...tree.querySelectorAll('small')].filter(node => node.checkVisibility());
    const wrapped = counts.filter(node => {
      const range = document.createRange();
      range.selectNodeContents(node);
      return range.getClientRects().length > 1;
    });
    return { fullWidth: expanded.clientWidth === tree.clientWidth, counts: counts.length, wrapped: wrapped.length };
  });
  assert.ok(layout.fullWidth && layout.counts > 0);
  assert.equal(layout.wrapped, 0);
}

async function verifyCourseMap(page, base) {
  await page.goto(new URL('/teaching-aihom/lessons/', base).href);
  const input = page.locator('#filter');
  const stages = page.locator('.map .stage:visible');
  const links = page.locator('.jump a:visible');
  const visibleIds = () => stages.evaluateAll(nodes => nodes.map(node => '#' + node.id));
  const jumpIds = () => links.evaluateAll(nodes => nodes.map(node => node.hash));
  const all = await visibleIds();
  assert.ok(all.length > 1);
  await input.fill('001');
  assert.deepEqual(await visibleIds(), ['#stage-foundation']);
  assert.deepEqual(await jumpIds(), await visibleIds());
  await links.tap();
  assert.equal(new URL(page.url()).hash, '#stage-foundation');
  await input.fill('nonexistent-course-0a9f');
  assert.equal(await links.count(), 0);
  assert.equal(await stages.count(), 0);
  assert.ok(await page.locator('.map .empty').isVisible());
  await input.fill('');
  assert.deepEqual(await jumpIds(), all);
  assert.deepEqual(await visibleIds(), all);
}

async function main() {
  const base = new URL(process.argv[2]);
  for (const width of [375, 390]) {
    // Playwright normally disables BFCache. Allow Chromium to use it on the second pass.
    const browser = await chromium.launch({
      channel: 'chrome', ignoreDefaultArgs: width === 390 ? ['--disable-back-forward-cache'] : [],
    });
    try {
      const page = await browser.newPage({ viewport: { width, height: 844 }, hasTouch: true, isMobile: true });
      page.setDefaultTimeout(12000);
      await page.addInitScript(() => {
        addEventListener('pageshow', event => { window.tagCacheRestore = event.persisted; });
      });
      await page.route('**/*', route => {
        const url = new URL(route.request().url());
        return url.origin === base.origin && url.pathname !== '/js/site-analytics.js' ? route.continue() : route.abort();
      });
      const restoredFromCache = await verifyTags(page, base);
      assert.equal(restoredFromCache, width === 390, `Unexpected BFCache mode at ${width}px`);
      await verifyCategoryTree(page, base);
      await verifyCourseMap(page, base);
      console.log(`Verified tag history (BFCache: ${restoredFromCache}), category counts and course navigation at ${width}px.`);
    } finally {
      await browser.close();
    }
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
