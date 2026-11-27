const assert = require('node:assert/strict');
const { mkdir } = require('node:fs/promises');
const path = require('node:path');
const { setTimeout: wait } = require('node:timers/promises');
const { chromium } = require('playwright-core');

const base = new URL(process.argv[2]);
const screenshotDir = process.argv[3];
const longArticle = '/article/wechat-77e2fc1117899d.html';
const tableArticle = '/article/wechat-1237d7e55a11d7.html#passage-56e4e1373a64';

async function capture(page, name) {
  if (!screenshotDir) return;
  await wait(350); // Let the native tap highlight fade in evidence screenshots.
  await page.screenshot({ path: path.join(screenshotDir, name + '.png') });
}

async function readerPage(browser, options = {}) {
  const context = await browser.newContext({ ...options, serviceWorkers: 'block' });
  await context.route('**/*', route => new URL(route.request().url()).origin === base.origin
    ? route.continue() : route.abort());
  await context.addInitScript(() => Object.defineProperty(navigator, 'doNotTrack', { value: '1' }));
  return context.newPage();
}

async function swipe(session, from, to) {
  const point = (x, y) => [{ x, y, id: 1 }];
  await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: point(from.x, from.y) });
  for (let frame = 1; frame <= 8; frame++) {
    const x = from.x + (to.x - from.x) * frame / 8;
    const y = from.y + (to.y - from.y) * frame / 8;
    await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: point(x, y) });
    await wait(20);
  }
  // Release after a short hold so the measurement does not include a fling.
  await wait(180);
  await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
}

async function checkMobile(browser, width, height) {
  const page = await readerPage(browser, { viewport: { width, height }, isMobile: true, hasTouch: true });
  const session = await page.context().newCDPSession(page);
  await page.goto(new URL(longArticle, base).href);
  const outline = page.locator('.outline details');
  await page.waitForFunction(() => !document.querySelector('.outline details').open);
  for (let i = 0; i < 3; i++) await swipe(session, { x: width / 2, y: height - 90 }, { x: width / 2, y: 150 });
  assert.ok(await page.evaluate(() => scrollY > innerHeight), 'test must start in the middle of the article');
  const body = page.locator('.article-main');
  const measure = () => body.evaluate(el => ({ width: el.clientWidth, top: el.getBoundingClientRect().top }));
  const before = await measure();
  const button = await outline.locator('summary').boundingBox();
  assert.ok(button.y >= 0 && button.y + button.height < height, 'closed contents control must be in view');
  await page.touchscreen.tap(button.x + button.width / 2, button.y + button.height / 2);
  await page.waitForFunction(() => document.querySelector('.outline details').open);
  const panel = await outline.boundingBox();
  assert.ok(panel.y >= 0 && panel.y + panel.height <= height, 'expanded contents must stay in view');
  const opened = await measure();
  assert.equal(opened.width, before.width);
  assert.ok(Math.abs(opened.top - before.top) < 2, 'opening contents moved the text being read');
  await capture(page, 'contents-open-' + width);
  await outline.locator('summary').tap();
  assert.equal(await outline.evaluate(el => el.open), false);
  await outline.locator('summary').tap();

  const link = outline.locator('a').nth(5);
  const target = decodeURIComponent((await link.getAttribute('href')).slice(1));
  await link.tap();
  await page.waitForFunction(id => decodeURIComponent(location.hash.slice(1)) === id &&
    !document.querySelector('.outline details').open, target);
  const placement = await page.evaluate(id => {
    const heading = document.getElementById(id).getBoundingClientRect();
    const control = document.querySelector('.outline').getBoundingClientRect();
    return { heading: heading.top, control: control.bottom, viewport: innerHeight };
  }, target);
  assert.ok(placement.heading >= placement.control - 1 && placement.heading < placement.viewport, 'chapter is obscured');
  assert.equal((await measure()).width, before.width);
  assert.equal(await page.locator('.post-body blockquote').first().evaluate(el => getComputedStyle(el).marginInline), '0px');
  await capture(page, 'chapter-' + width);

  await page.goto(new URL(tableArticle, base).href);
  const table = page.locator('#passage-56e4e1373a64');
  const tableWidth = await table.evaluate(el => el.scrollWidth);
  assert.ok(tableWidth > await table.evaluate(el => el.clientWidth) && tableWidth < width * 4, 'data table should wrap long prose');
  const bounds = await table.boundingBox();
  const y = Math.max(bounds.y + 20, (await page.locator('.outline').boundingBox()).y + 80);
  await swipe(session, { x: bounds.x + bounds.width - 15, y }, { x: bounds.x + 15, y });
  assert.ok(await table.evaluate(el => el.scrollLeft > 20), 'data table must accept a horizontal swipe');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
  await capture(page, 'table-' + width);

  const panelWithLongLines = page.locator('.code-panel').filter({ has: page.getByRole('button', { name: '自动换行' }) }).first();
  const wrap = panelWithLongLines.getByRole('button', { name: '自动换行' });
  const code = panelWithLongLines.locator('.code-scroll');
  await code.evaluate(el => el.scrollIntoView({block: 'center'}));
  const codeBounds = await code.boundingBox();
  const codeY = (Math.max(0, codeBounds.y) + Math.min(height, codeBounds.y + codeBounds.height)) / 2;
  await swipe(session, {x: codeBounds.x + codeBounds.width - 15, y: codeY}, {x: codeBounds.x + 15, y: codeY});
  assert.ok(await code.evaluate(el => el.scrollLeft > 0), 'original code must scroll horizontally');
  await wrap.tap();
  assert.equal(await wrap.getAttribute('aria-pressed'), 'true');
  await wrap.tap();
  assert.equal(await wrap.getAttribute('aria-pressed'), 'false');
  await page.goto(new URL('/article/traffic-replay-diff-report.html', base).href);
  const comparison = page.locator('.article-comparison').first();
  assert.equal(await comparison.evaluate(el => getComputedStyle(el).tableLayout), 'fixed');
  assert.ok(await comparison.evaluate(el => el.clientWidth <= el.parentElement.clientWidth + 1));
  console.log(width + 'px: chapter navigation, stable ' + before.width + 'px reading width, quoted text, ' + tableWidth + 'px data table, fixed comparison table and scrollable code verified.');
  await page.context().close();
}

async function main() {
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    await checkMobile(browser, 320, 700);
    await checkMobile(browser, 390, 844);
    const page = await readerPage(browser, { viewport: { width: 1440, height: 900 } });
    await page.goto(new URL(longArticle, base).href);
    const outline = page.locator('.outline details');
    assert.ok(await outline.evaluate(el => el.open));
    const body = await page.locator('.article-main').boundingBox();
    assert.ok((await outline.boundingBox()).x >= body.x + body.width);
    await outline.locator('summary').click();
    assert.equal(await outline.evaluate(el => el.open), false);
    await outline.locator('summary').click();
    assert.equal(await outline.evaluate(el => el.open), true);
    console.log('Desktop sidebar opens and collapses.');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
