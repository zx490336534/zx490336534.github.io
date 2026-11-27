const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');

async function main() {
  const base = new URL(process.argv[2]);
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    await page.route('**/*', route => new URL(route.request().url()).origin === base.origin
      ? route.continue() : route.abort());
    const background = () => page.locator('body').evaluate(body => getComputedStyle(body).backgroundColor);
    const goto = path => page.goto(new URL(path, base).href);
    await page.emulateMedia({ colorScheme: 'light' });
    await goto('/lab/');
    await page.locator('#site-appearance').selectOption('dark');
    const dark = await background();
    await page.locator('main a[href="/teaching-aihom/lessons/index.html"]').tap();
    assert.equal(await background(), dark, 'The AIHom map must inherit the blog preference');
    for (const path of ['/teaching-aihom/lessons/aihom/0060-cross-repo-integration.html',
                        '/teaching-kuai/lessons/index.html', '/teaching-kuai/lessons/front/0005-kuai-front-overview.html']) {
      await goto(path);
      assert.equal(await background(), dark, path);
      if (path.includes('0060-')) {
        const answer = page.locator('#quiz1 .quiz-options button').first();
        await answer.tap();
        const result = page.locator('#quiz1 .quiz-feedback');
        assert.ok(await result.isVisible());
        await page.waitForFunction(() => {
          const button = document.querySelector('#quiz1 button.wrong');
          const feedback = document.querySelector('#quiz1 .quiz-feedback');
          return button && getComputedStyle(button).backgroundColor === getComputedStyle(feedback).backgroundColor;
        });
      }
    }
    await page.emulateMedia({ colorScheme: 'dark' });
    await goto('/lab/');
    await page.locator('#site-appearance').selectOption('light');
    await page.locator('main a[href="/teaching-kuai/lessons/index.html"]').tap();
    const light = await background();
    assert.notEqual(light, dark, 'Explicit light takes precedence over a dark OS');
    await goto('/lab/');
    await page.locator('#site-appearance').selectOption('system');
    await page.locator('main a[href="/teaching-kuai/lessons/index.html"]').tap();
    assert.equal(await background(), dark);
    await page.emulateMedia({ colorScheme: 'light' });
    await page.waitForFunction(expected => getComputedStyle(document.body).backgroundColor === expected, light);
    console.log('Both course maps and lessons inherit the blog appearance; system changes apply in place.');
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
