import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';

const slug = process.env.UMAMI_COUNTS_SHARE ?? '';
if (!/^[A-Za-z0-9_-]{10,80}$/.test(slug)) throw new Error('Missing read-only Umami share in GitHub Secrets');

const require = createRequire(process.env.RUNNER_TEMP + '/blog-counter-deps/package.json');
const { chromium } = require('playwright-core');
const website = (await readFile('index.html', 'utf8')).match(/id="site-analytics"[^>]*data-website-id="([^"]+)"/)?.[1];
if (!website) throw new Error('Website ID not found');
const posts = JSON.parse(await readFile('search.json', 'utf8'));
const articles = posts.map(post => post.path);
const wechatRank = JSON.parse(await readFile('scripts/popular_seed.json', 'utf8'));
const seedOrder = new Map(wechatRank.map((path, index) => [path, index]));
const previous = process.argv[3] ? JSON.parse(await readFile(process.argv[3], 'utf8')) : null;
const code = await readFile('scripts/public-counts.browser.js', 'utf8');
const collect = new Function('return ' + code)();

try {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    const page = await browser.newPage();
    const response = await page.goto('https://cloud.umami.is/share/' + slug, {waitUntil: 'domcontentloaded', timeout: 15000});
    if (!response?.ok()) throw new Error('Read-only dashboard returned HTTP ' + response?.status());
    if (new URL(page.url()).hostname !== 'cloud.umami.is') throw new Error('Unexpected analytics dashboard host');
    const {articleClicks, articleClickError, ...stats} = await page.evaluate(collect, {api: 'https://gateway-us.umami.is/api', slug, website, articles, previous});
    if (articleClickError) {
      console.warn('Article click aggregation failed: ' + articleClickError.split(slug).join('[redacted]'));
      stats.articleClickCheckpoint = previous?.articleClickCheckpoint;
      stats.popularArticles = previous?.popularArticles;
    } else {
      stats.popularArticles = posts.filter(post => articleClicks[post.path] > 0)
        .sort((a, b) => articleClicks[b.path] - articleClicks[a.path] ||
          (seedOrder.get(a.path) ?? wechatRank.length) - (seedOrder.get(b.path) ?? wechatRank.length))
        .slice(0, wechatRank.length)
        .map(({path, title, cover}) => ({path, title, cover, clicks: articleClicks[path]}));
    }
    await writeFile(process.argv[2], JSON.stringify(stats) + '\n');
    console.log('Updated public counts for ' + Object.keys(stats.reads).length + ' articles. ' +
      (stats.popularArticles?.length ?? 0) + ' articles on the click leaderboard.');
  } finally {
    await browser.close();
  }
} catch (error) {
  console.error(error.message.split(slug).join('[redacted]'));
  process.exitCode = 1;
}
