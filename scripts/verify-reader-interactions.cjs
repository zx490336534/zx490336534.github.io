const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { chromium } = require('playwright-core');

async function main() {
  const base = new URL(process.argv[2]);
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    const page = await browser.newPage();
    await page.route('**/*', route => new URL(route.request().url()).origin === base.origin
      ? route.continue() : route.abort());
    await page.addInitScript(() => {
      Object.defineProperty(navigator.clipboard, 'writeText', {
        value: async value => { window.copiedExample = value; },
      });
    });
    await page.goto(new URL('/article/wechat-b60d807fd0df46.html', base).href);
    const panel = page.locator('.code-panel').filter({ hasText: '__radd__' }).first();
    await panel.getByRole('button', { name: '复制代码' }).click();
    await panel.getByRole('button', { name: '已复制' }).waitFor();
    const copied = await page.evaluate(() => window.copiedExample);
    assert.match(copied, /def __radd__\(self, other\):/);
    execFileSync('python3', ['-c', 'import ast, sys; ast.parse(sys.stdin.read())'], { input: copied });

    await page.goto(new URL('/videos/', base).href);
    await page.getByLabel('按片名或系列筛选视频', { exact: true }).fill('爬取淘宝');
    const matches = page.locator('.video-shelf:visible li:visible a');
    assert.equal(await matches.count(), 1);
    assert.equal(await matches.first().getAttribute('href'), '/article/44218b5c.html#article-video-title');
    await matches.first().click();
    await page.locator('.article-video .video-transcript summary').click();
    assert.ok(await page.locator('.article-video .video-transcript p:visible').count());
    console.log('Verified copied Python, video filtering, direct playback link and transcript.');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
