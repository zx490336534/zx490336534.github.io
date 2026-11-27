const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');

async function main() {
  const base = new URL(process.argv[2]);
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    for (const width of [390, 1440]) {
      const context = await browser.newContext({
        viewport: {width, height: 900}, isMobile: width === 390, hasTouch: width === 390,
        javaScriptEnabled: false, serviceWorkers: 'block'
      });
      await context.route('**/*', route => new URL(route.request().url()).origin === base.origin
        ? route.continue() : route.abort());
      const page = await context.newPage();
      const category = '/categories/testing/quality/';
      const promptfoo = '/article/promptfoo-agent-regression.html';
      const replay = '/article/kitaru-agent-replay-regression.html';
      assert.ok((await page.goto(new URL(category, base).href)).ok());
      const area = page.locator('.catalog-results');
      await area.locator(`a.row-title[href="${promptfoo}"]`).click();
      assert.equal(new URL(page.url()).pathname, promptfoo);
      const reading = page.getByRole('navigation', {name: '延伸阅读'});
      assert.ok(await reading.isVisible());
      await page.waitForLoadState('load');
      await page.waitForFunction(expected => document.documentElement.scrollWidth === expected, width);
      await reading.locator(`a[href="${replay}"]`).click();
      assert.equal(new URL(page.url()).pathname, replay);
      await page.locator('.read-next-topic').click();
      assert.equal(new URL(page.url()).pathname, category);
      await page.waitForLoadState('load');
      await page.waitForFunction(expected => document.documentElement.scrollWidth === expected, width);
      await context.close();
    }
    console.log('Mobile and desktop: category → article → topical next read → category, without JavaScript.');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
