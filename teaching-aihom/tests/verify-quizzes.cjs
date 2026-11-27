const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');

const base = new URL(process.argv[2]);
const lessons = path.resolve(__dirname, '../lessons');
const files = fs.readdirSync(lessons, { recursive: true }).filter(name =>
  name.endsWith('.html') && fs.readFileSync(path.join(lessons, name), 'utf8').includes('class="quiz-options"'));
const lessonUrl = name => new URL('/teaching-aihom/lessons/' + name.split(path.sep).join('/'), base).href;

async function gradeAll(page, correct) {
  return page.locator('.quiz-options').evaluateAll((groups, correct) => groups.map(group => {
    const buttons = [...group.children];
    const expected = group.hasAttribute('data-correct') ? Number(group.dataset.correct)
      : buttons.findIndex(b => b.dataset.correct === 'true' || /,\s*true\s*\)/.test(b.getAttribute('onclick')));
    if (buttons.length < 2 || expected < 0 || expected >= buttons.length) throw Error('Missing answer key');
    if (group.getAttribute('role') !== 'group' || !document.getElementById(group.getAttribute('aria-labelledby'))?.textContent.trim())
      throw Error('Missing question label');
    if (buttons.some(b => b.tagName !== 'BUTTON' || b.type !== 'button' || b.tabIndex < 0 || !b.textContent.trim()))
      throw Error('Missing native answer button');
    const selected = buttons[correct ? expected : (expected + 1) % buttons.length];
    selected.click();
    const result = group.parentElement.querySelector('.quiz-feedback[role="status"]');
    if (!selected.classList.contains(correct ? 'correct' : 'wrong') || !result?.innerText.trim())
      throw Error('Missing grade or explanation in ' + group.parentElement.id);
    return result.innerText;
  }), correct);
}

async function main() {
  assert(files.length, 'No quiz lessons found');
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: 'chrome' });
  try {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    await context.route('**/*', route => {
      const request = route.request();
      return new URL(request.url()).origin === base.origin && ['document', 'stylesheet'].includes(request.resourceType())
        ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let questions = 0;
    for (const file of files) {
      await page.goto(lessonUrl(file));
      const right = await gradeAll(page, true);
      await page.reload();
      const wrong = await gradeAll(page, false);
      assert(right.length && right.every((text, i) => text !== wrong[i]), 'Same or missing feedback in ' + file);
      assert.deepEqual(errors, [], file);
      questions += right.length;
    }

    // Exercise actual focus traversal and native keyboard/touch activation on a formerly broken lesson.
    for (const action of ['Enter', 'Space', 'tap']) {
      await page.goto(lessonUrl('aihom/0060-cross-repo-integration.html'));
      const group = page.getByRole('group').first();
      const buttons = group.getByRole('button');
      await buttons.first().focus();
      await page.keyboard.press('Tab');
      assert(await buttons.nth(1).evaluate(button => button === document.activeElement));
      if (action === 'tap') await buttons.nth(1).tap();
      else await page.keyboard.press(action);
      const status = page.getByRole('status').first();
      const answered = await status.innerText();
      assert(answered.includes('postMessage'), action);
      await buttons.first().evaluate(button => button.click());
      assert.equal(await status.innerText(), answered, 'A completed question was graded twice');
    }
    console.log(`Verified ${questions} quizzes in ${files.length} lessons, both grades, keyboard and touch.`);
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
