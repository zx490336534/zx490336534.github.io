import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';

const slug = process.env.UMAMI_COUNTS_SHARE ?? '';
if (!/^[A-Za-z0-9_-]{10,80}$/.test(slug)) throw new Error('Missing read-only Umami share in GitHub Secrets');

const require = createRequire(process.env.RUNNER_TEMP + '/blog-counter-deps/package.json');
const { chromium } = require('playwright-core');
const website = (await readFile('index.html', 'utf8')).match(/id="site-analytics"[^>]*data-website-id="([^"]+)"/)?.[1];
if (!website) throw new Error('Website ID not found');
const articles = JSON.parse(await readFile('search.json', 'utf8')).map(post => post.path);
const code = await readFile('scripts/public-counts.browser.js', 'utf8');
const collect = new Function('return ' + code)();

try {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    const page = await browser.newPage();
    const response = await page.goto('https://cloud.umami.is/share/' + slug, {waitUntil: 'domcontentloaded', timeout: 15000});
    if (!response?.ok()) throw new Error('Read-only dashboard returned HTTP ' + response?.status());
    if (new URL(page.url()).hostname !== 'cloud.umami.is') throw new Error('Unexpected analytics dashboard host');
    const stats = await page.evaluate(collect, {api: 'https://gateway-us.umami.is/api', slug, website, articles});
    await writeFile(process.argv[2], JSON.stringify(stats) + '\n');
    console.log('Updated public counts for ' + Object.keys(stats.reads).length + ' articles.');
  } finally {
    await browser.close();
  }
} catch (error) {
  console.error(error.message.split(slug).join('[redacted]'));
  process.exitCode = 1;
}
