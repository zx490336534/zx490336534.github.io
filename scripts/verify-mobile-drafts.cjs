const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');

const pageUrl = new URL('/tools/test-cases/', process.argv[2]);
const gateway = 'https://draft-test.invalid/v1';
const summary = '已生成邀请测试用例。';
const success = { summary, cases: [{ id: 'one', category: '邀请', priority: 'P1', topic: '已撤销的邀请失效',
  precondition: '存在邀请', steps: '撤销并打开邀请', expected: '拒绝加入' }] };
const draftA = '会话甲：已撤销的邀请不能加入团队。';
const draftB = '会话乙：删除成员后收回访问权限。';
const saved = '未发送草稿已保存在本标签页';
const volatile = '草稿仅保留在当前页面，刷新后可能丢失';

async function verify(browser, blocked) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    serviceWorkers: 'block' });
  let fail = true;
  let pending;
  let release;
  if (blocked) await context.addInitScript(() => {
    for (const method of ['getItem', 'setItem', 'removeItem']) {
      const original = Storage.prototype[method];
      Storage.prototype[method] = function (key, ...args) {
        if (key.startsWith('next-ai-test-cases:composer:')) throw new DOMException('Unavailable', 'QuotaExceededError');
        return original.call(this, key, ...args);
      };
    }
  });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.href === gateway + '/chat/completions') {
      if (pending) await pending;
      const response = fail ? { error: { message: '模拟模型拒绝请求' } } : { choices: [{ message: { content: JSON.stringify(success) } }] };
      return route.fulfill({ status: fail ? 400 : 200, json: response });
    }
    if (route.request().method() === 'GET' && url.origin === pageUrl.origin &&
        [pageUrl.pathname, '/css/entry-nav.css'].includes(url.pathname)) return route.continue();
    return route.abort();
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const field = page.locator('textarea:visible');
  const button = name => page.getByRole('button', { name, exact: true });
  const assertDraft = async text => {
    await field.waitFor();
    await page.waitForFunction(expected => [...document.querySelectorAll('textarea')].some(
      input => input.getClientRects().length && input.value === expected), text);
    if (text) await page.getByText(blocked ? volatile : saved, { exact: true }).waitFor();
  };
  async function rename(title) {
    await button('历史').tap();
    await button('重命名 新会话').first().tap();
    await page.getByRole('textbox', { name: '会话名称' }).fill(title);
    await button('保存名称').tap();
    await button(title).waitFor();
    await button('AI 对话').tap();
  }
  async function select(title) {
    await button('历史').tap();
    await button(title).tap();
    await button('AI 对话').tap();
  }
  try {
    await page.goto(pageUrl.href);
    await field.fill(draftA);
    await assertDraft(draftA);
    await rename('草稿甲');
    await button('新建会话').tap();
    await assertDraft('');
    await field.fill(draftB);
    await rename('草稿乙');
    await select('草稿甲');
    await assertDraft(draftA);
    await select('草稿乙');
    await assertDraft(draftB);
    await field.fill('');
    await select('草稿甲');
    await assertDraft(draftA);
    await select('草稿乙');
    await assertDraft('');
    await select('草稿甲');
    await page.reload();
    await assertDraft(blocked ? '' : draftA);
    if (blocked) return;

    await button('模型设置').tap();
    const settings = page.getByRole('dialog', { name: '模型设置' });
    await settings.getByRole('textbox', { name: '模型名' }).fill('fixture');
    await settings.getByRole('textbox', { name: 'Base URL' }).fill(gateway);
    await settings.getByLabel('API Key').fill('local-test-fixture');
    await settings.getByRole('button', { name: '保存', exact: true }).tap();
    await button('发送').tap();
    await page.getByRole('alert').filter({ hasText: 'HTTP 400' }).waitFor();
    await assertDraft(draftA);
    fail = false;
    pending = new Promise(resolve => { release = resolve; });
    const inFlight = page.waitForRequest(gateway + '/chat/completions');
    await button('发送').tap();
    await inFlight;
    await field.fill('发送期间输入的下一条草稿');
    release();
    pending = undefined;
    await page.getByText(summary, { exact: true }).waitFor();
    await assertDraft('发送期间输入的下一条草稿');

    await select('草稿乙');
    await field.fill(draftB);
    await button('发送').tap();
    await page.getByText(summary, { exact: true }).waitFor();
    await page.waitForFunction(() => document.querySelector('textarea')?.value === '');
    await page.reload();
    await button('AI 对话').tap();
    await page.getByText(summary, { exact: true }).waitFor();
    await assertDraft('');
  } finally {
    release?.();
    await context.close();
    assert.deepEqual(errors, []);
  }
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  try {
    await verify(browser, false);
    await verify(browser, true);
    console.log('Verified per-session drafts, reload, failed and successful sends, concurrent typing and storage fallback.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
