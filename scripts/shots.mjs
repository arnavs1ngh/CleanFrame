// Development only. Screenshots every fixture scenario x List/Dock x two
// resolutions, plus a handful of named focus states, and composites them
// into a single contact sheet for quick review. Output: .local/shots/
//
// house-api.js doesn't exist yet (Phase 2), so right now every scenario
// renders identically - this just proves the tool works end to end. Once
// the weather strip, calendar panel and Home Assistant panel are wired up
// in Phase 3, these same screenshots will start showing real differences,
// and the FOCUS_STATES list below should grow to include "weather strip
// focused", "calendar panel open" and "a tile mid-action".
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { openPreview, root } from './browser.mjs';

const OUT = root + '.local/shots/';
mkdirSync(OUT, { recursive: true });

const FIXTURES_DIR = root + 'dev/fixtures/v1/';
const SCENARIOS = readdirSync(FIXTURES_DIR).filter(n => n.endsWith('.json')).map(n => n.slice(0, -5)).sort();
const LAYOUTS = [{ id: 'list', theme: 'list' }, { id: 'dock', theme: 'shore' }];
const SIZES = [{ id: '1920x1080', width: 1920, height: 1080 }, { id: '1280x720', width: 1280, height: 720 }];

// Placeholder set: these already exist today. Replace/extend once Phase 3 lands.
const FOCUS_STATES = [
  { id: 'home-idle', layout: 'list', apply: async () => {} },
  { id: 'controls-focused', layout: 'list', apply: async page => { await page.evaluate(() => ShoreQA.nav('right')); } },
  { id: 'settings-open', layout: 'dock', apply: async page => { await page.evaluate(() => ShoreQA.scene('settings')); } }
];

function seedFor(theme) {
  // Mirrors the legacy migration: 'list' -> Dark/List/Type, 'shore' -> Photo/Dock/Glass.
  return { dock: ['jellyfin', 'netflix', 'bbc', 'itvx'], wallpaper: 'misty', mode: 'fixed', lastApp: 'netflix', theme };
}

async function newPage(preview, { width, height }, theme, scenario) {
  const page = await preview.browser.newPage({ viewport: { width, height } });
  page.setDefaultTimeout(10000);
  const fixture = readFileSync(FIXTURES_DIR + scenario + '.json');
  // Decoupled from however Phase 2's house-api.js builds its request URL.
  await page.route('**/v1/home*', route => route.fulfill({ status: 200, contentType: 'application/json', body: fixture }));
  await page.addInitScript(seed => { localStorage.setItem('cleanframe.home.v1', JSON.stringify(seed)); }, seedFor(theme));
  await page.goto(preview.baseURL + '/home/');
  await page.waitForFunction(() => window.ShoreQA && typeof ShoreQA.ready === 'function' && ShoreQA.ready(), null, { timeout: 15000 });
  await page.waitForLoadState('networkidle');
  return page;
}

async function main() {
  const preview = await openPreview();
  const shots = [];
  try {
    for (const scenario of SCENARIOS) {
      for (const layout of LAYOUTS) {
        for (const size of SIZES) {
          const page = await newPage(preview, size, layout.theme, scenario);
          const name = scenario + '--' + layout.id + '--' + size.id + '.png';
          await page.screenshot({ path: OUT + name });
          shots.push({ name, group: scenario, col: layout.id + ' ' + size.id });
          await page.close();
        }
      }
    }
    for (const state of FOCUS_STATES) {
      const theme = LAYOUTS.find(l => l.id === state.layout).theme;
      const page = await newPage(preview, SIZES[0], theme, 'normal');
      await state.apply(page);
      await page.waitForTimeout(150);
      const name = 'focus--' + state.id + '.png';
      await page.screenshot({ path: OUT + name });
      shots.push({ name, group: 'focus states', col: state.id });
      await page.close();
    }
  } finally {
    await preview.close();
  }
  await buildContactSheet(shots);
  console.log('Wrote ' + shots.length + ' screenshots and a contact sheet to ' + OUT);
}

async function buildContactSheet(shots) {
  const groups = [...new Set(shots.map(s => s.group))];
  const rows = groups.map(group => {
    const cells = shots.filter(s => s.group === group).map(s => {
      const b64 = readFileSync(OUT + s.name).toString('base64');
      return '<figure><img src="data:image/png;base64,' + b64 + '"><figcaption>' + s.col + '</figcaption></figure>';
    }).join('');
    return '<section><h2>' + group + '</h2><div class="row">' + cells + '</div></section>';
  }).join('');
  const html = '<!doctype html><html><head><meta charset="utf-8"><style>' +
    'body{margin:0;background:#111;font-family:sans-serif;color:#eee}' +
    'h2{padding:12px 16px 4px;margin:0;font-size:14px;color:#9cf}' +
    '.row{display:flex;flex-wrap:wrap;gap:10px;padding:0 16px 16px}' +
    'figure{margin:0;width:360px}' +
    'img{width:100%;display:block;border:1px solid #333}' +
    'figcaption{font-size:11px;color:#aaa;padding:2px 0}' +
    '</style></head><body>' + rows + '</body></html>';
  const sheetHtmlPath = OUT + 'contact-sheet.html';
  writeFileSync(sheetHtmlPath, html);
  const preview = await openPreview();
  try {
    const page = await preview.browser.newPage({ viewport: { width: 1600, height: 1200 } });
    await page.goto('file://' + sheetHtmlPath);
    await page.screenshot({ path: OUT + 'contact-sheet.png', fullPage: true });
    await page.close();
  } finally {
    await preview.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
