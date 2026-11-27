const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');

async function main() {
  const base = new URL(process.argv[2]);
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    const page = await browser.newPage({ viewport: { width: 375, height: 844 }, isMobile: true, hasTouch: true });
    await page.route('**/*', route => new URL(route.request().url()).origin === base.origin
      ? route.continue() : route.abort());
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'clipboard', {
        configurable: true, value: { writeText: async text => { window.__lessonClipboard = text; } }
      });
    });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const background = () => page.locator('body').evaluate(body => getComputedStyle(body).backgroundColor);
    const goto = async path => assert.equal((await page.goto(new URL(path, base).href)).status(), 200, path);
    const overflow = () => page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    await page.emulateMedia({ colorScheme: 'light' });
    await goto('/lab/');
    await page.locator('#site-appearance').selectOption('dark');
    const dark = await background();
    let checkedLessons = 0;
    for (const [course, intro, normal, fault, capNormal, capFault] of [
      ['aihom', 'request', '更新为版本 3', '保留旧布局', '版本 4', '版本 3'],
      ['kuai', 'job', '3 条通过', '1 条执行异常', '发布门槛：通过', '发布门槛：拦截'],
    ]) {
      await goto('/lab/');
      const prefix = '/teaching-' + course + '/lessons/';
      await Promise.all([page.waitForURL(new URL(prefix + 'index.html', base).href),
        page.locator('main a[href="' + prefix + 'index.html"]').tap()]);
      assert.equal(await background(), dark, 'The course shares the exact blog palette');
      assert.equal(await page.locator('.masthead nav a[aria-current]').getAttribute('href'), '/lab/');
      assert.equal(await overflow(), false, prefix);
      const links = await page.locator('.lesson-tile a').evaluateAll(items => items.map(item => item.href));
      assert.ok(links.length > 8);
      checkedLessons += links.length;
      const stages = await page.locator(".stage:visible").count();
      assert.ok(stages > 3);
      await page.locator('#filter').fill('nonsense-not-a-course');
      assert.equal(await page.locator('.stage:visible').count(), 0);
      await page.locator('#clear-filter').tap();
      assert.equal(await page.locator('.stage:visible').count(), stages);
      await Promise.all([page.waitForURL(new URL(prefix + intro + '.html', base).href),
        page.locator('#resume').tap()]);
      await page.locator('[data-run=normal]').tap();
      assert.ok((await page.locator('output').innerText()).includes(normal));
      await page.locator('[data-run=fault]').tap();
      assert.ok((await page.locator('output').innerText()).includes(fault));

      for (const link of links) {
        await goto(link);
        assert.equal(await background(), dark, link);
        assert.equal(await overflow(), false, link);
        const quiz = page.locator('.course-quiz');
        const answer = Number(await quiz.getAttribute('data-answer'));
        const choices = quiz.locator('input[type=radio]');
        await choices.nth(1 - answer).check();
        await quiz.locator('button').tap();
        assert.equal(await quiz.locator('[role=status]').getAttribute('data-state'), 'wrong');
        await choices.nth(answer).check();
        await quiz.locator('button').tap();
        assert.equal(await quiz.locator('[role=status]').getAttribute('data-state'), 'correct');
        const deep = page.locator('#code-walkthrough');
        assert.ok(await deep.isVisible());
        assert.ok(await deep.locator('.course-flow li').count() >= 3);
        assert.ok(await page.locator('#failure-cases .failure-card').count() >= 2);
        const snippet = deep.locator('.snippet');
        assert.equal(await snippet.evaluate(el => el.open), true);
        if (link === links[0]) {
          await snippet.locator('[data-copy-example]').tap();
          assert.equal(await page.evaluate(() => window.__lessonClipboard), await snippet.locator('pre code').textContent());
        }
        await snippet.locator('summary').tap();
        assert.equal(await snippet.evaluate(el => el.open), false);
      }
      await goto(prefix + 'capstone.html');
      await page.locator('[data-run=normal]').tap();
      assert.ok((await page.locator('output').innerText()).includes(capNormal));
      await page.locator('[data-run=fault]').tap();
      assert.ok((await page.locator('output').innerText()).includes(capFault));
      assert.ok(await page.locator('.reference-project a[download]').isVisible());

      await goto(prefix + intro + '.html');
      await page.locator('#complete-lesson').tap();
      await page.reload();
      assert.equal(await page.locator('#complete-lesson').getAttribute('aria-pressed'), 'true');
      await goto(prefix + 'index.html');
      assert.equal(await page.locator('.lesson-state').first().innerText(), '已学');
      assert.ok((await page.locator('#progress-text').innerText()).endsWith('1 / ' + links.length));
      assert.equal(await page.locator('#resume').innerText(), '继续学习');
      // Reproduce a previously saved record from before the course expanded.
      const oldKeys = course === 'aihom' ? ['service', 'stream'] : ['contract', 'dashboard'];
      await page.evaluate(([id, done, last]) => {
        localStorage.setItem('public-course-v1-teaching-' + id, JSON.stringify({ done: [done], last }));
      }, [course, ...oldKeys]);
      await page.reload();
      assert.equal(await page.locator(`[data-lesson="${oldKeys[0]}"] .lesson-state`).innerText(), '已学');
      assert.equal(await page.locator('#resume').getAttribute('href'), oldKeys[1] + '.html');
    }
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.locator('#site-appearance').selectOption('light');
    const light = await background();
    assert.notEqual(light, dark, 'Explicit light takes precedence over a dark OS');
    await page.locator('#site-appearance').selectOption('system');
    assert.equal(await background(), dark);
    await page.emulateMedia({ colorScheme: 'light' });
    await page.waitForFunction(expected => getComputedStyle(document.body).backgroundColor === expected, light);
    assert.deepEqual(errors, []);

    const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false });
    for (const path of ['/teaching-aihom/lessons/index.html', '/teaching-kuai/lessons/index.html']) {
      await desktop.goto(new URL(path, base).href);
      assert.ok(await desktop.locator('.lesson-tile a:visible').count() > 8);
      await desktop.locator('.lesson-tile a').first().click();
      assert.ok(await desktop.locator('article #scene').isVisible());
      assert.ok(await desktop.locator('noscript details').isVisible());
      assert.equal(await desktop.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    }
    console.log(`Public courses: ${checkedLessons} mobile lessons, shared theme, simulations, maps, progress, folded code and no-JS reading.`);
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
