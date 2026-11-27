const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { chromium } = require('playwright-core');
const fixture = readFileSync(join(__dirname, 'fixtures/video-series-clip.mp4'));

async function main() {
  const base = new URL(process.argv[2]);
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const requested = [];
    function mock(route) {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin === base.origin) return route.continue();
      if (request.resourceType() === 'media' && url.hostname === 'github.com') {
        requested.push(url.pathname);
        return route.fulfill({ body: fixture, contentType: 'video/mp4' });
      }
      return route.abort();
    }
    await desktop.route('**/*', mock);
    await desktop.goto(new URL('/videos/', base).href);
    assert.equal(await desktop.locator('.vc-grid .vc-card').count() > 25, true);
    await desktop.locator('.vc-hero .vc-start').click();
    const entries = desktop.locator('[data-player-episode]');
    const first = await entries.nth(0).getAttribute('data-player-episode');
    const second = await entries.nth(1).getAttribute('data-player-episode');
    const last = await entries.last().getAttribute('data-player-episode');
    await desktop.waitForFunction(first => document.querySelector('[aria-current="true"][data-player-episode]')?.dataset.playerEpisode === first, first);
    assert.equal(await desktop.locator('video').evaluate(v => v.paused), true, 'entry must not play until user starts');
    assert.equal(await desktop.locator('[data-autonext]').isChecked(), true);
    await desktop.locator('video').evaluate(v => { window.seriesPlayer = v; v.muted = true; });
    await desktop.getByRole('button', {name: '下一集', exact: true}).click();
    await desktop.waitForFunction(second => {
      const v = document.querySelector('video');
      return new URL(location.href).searchParams.get('episode') === second && v === window.seriesPlayer && v.readyState >= 2;
    }, second);
    assert.equal(await desktop.locator('[data-player-article]').getAttribute('href'), await entries.nth(1).getAttribute('data-article'));
    const original = desktop.locator('[data-player-article]');
    assert.equal(await original.getAttribute('target'), '_blank');
    assert.equal(await original.getAttribute('rel'), 'noopener');
    assert.equal(await desktop.getByText('打开原文播放器', { exact: false }).count(), 0);
    const articleLink = await original.getAttribute('href');
    const [openedArticle] = await Promise.all([desktop.waitForEvent('popup'), original.click()]);
    await openedArticle.waitForURL(new URL(articleLink, base).href);
    assert.ok(new URL(desktop.url()).pathname.startsWith('/videos/series/'));
    await openedArticle.close();

    const secondSource = new URL(await entries.nth(1).getAttribute('data-src')).pathname;
    assert.ok(requested.includes(secondSource), 'must actually load the selected file');
    // An actual 1.25s native MP4 ends, yielding the next video on the same element.
    const third = await entries.nth(2).getAttribute('data-player-episode');
    await desktop.waitForFunction(third => {
      const v = document.querySelector('video');
      return new URL(location.href).searchParams.get('episode') === third && v === window.seriesPlayer && v.readyState >= 2;
    }, third);
    assert.ok(requested.includes(new URL(await entries.nth(2).getAttribute('data-src')).pathname));
    await desktop.locator('[data-autonext]').uncheck();
    await desktop.locator('video').evaluate(v => { v.pause(); v.dispatchEvent(new Event('ended')); });
    assert.equal(new URL(desktop.url()).searchParams.get('episode'), third);
    assert.match(await desktop.locator('[data-player-status]').textContent(), /本集已播放完毕/);
    await desktop.locator('[data-autonext]').check();
    await desktop.locator('video').evaluate(v => {
      v.play = () => Promise.reject(new DOMException('test', 'NotAllowedError'));
      v.dispatchEvent(new Event('ended'));
    });
    await desktop.getByRole('button', {name: '点击播放'}).waitFor();
    assert.match(await desktop.locator('[data-player-status]').textContent(), /浏览器需要你点一下/);
    const path = new URL(desktop.url()).pathname;
    await desktop.goto(new URL(path + '?episode=' + last, base).href);
    assert.equal(await entries.last().getAttribute('aria-current'), 'true');
    await desktop.locator('video').evaluate(v => v.dispatchEvent(new Event('ended')));
    assert.equal(new URL(desktop.url()).searchParams.get('episode'), last);
    assert.match(await desktop.locator('[data-player-status]').textContent(), /本系列已播放完毕/);
    assert.equal(await desktop.locator('[data-next]').isDisabled(), true);
    await desktop.locator('[data-autonext]').uncheck();
    await desktop.reload();
    assert.equal(await desktop.locator('[data-autonext]').isChecked(), false, 'preference survives reload');
    await desktop.goto(new URL('/videos/watch/promptfoo-agent-regression/', base).href);
    assert.ok(await desktop.locator('.watch-transcript p').count());

    const mobile = await browser.newPage({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    await mobile.route('**/*', mock);
    await mobile.goto(new URL('/videos/', base).href);
    assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await Promise.all([mobile.waitForURL(new URL(path, base).href), mobile.locator('.vc-hero .vc-start').tap()]);
    assert.equal(await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.ok(await mobile.locator('.vp-queue').isVisible());
    const nojs = await browser.newPage({ javaScriptEnabled: false });
    await nojs.route('**/*', mock);
    await nojs.goto(new URL(path, base).href);
    assert.ok(await nojs.locator('video').isVisible());
    assert.match(await nojs.locator('[data-player-episode]').first().getAttribute('href'), /^\/(?:article\/|videos\/watch\/)/);
    console.log('Video series: native media ended → same-player auto-next, correct source, opt-out, retry fallback, stop at last episode, responsive layouts and static links.');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
