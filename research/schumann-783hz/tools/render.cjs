// Headless Chromium helpers for the build (Playwright is preinstalled in this environment).
//   node tools/render.cjs pdf  <input.html> <output.pdf>
//   node tools/render.cjs png  <figures_dir> <out_dir>        (SVG -> PNG at 2x, for DOCX)
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [mode, a, b] = process.argv.slice(2);
  const browser = await chromium.launch();
  try {
    if (mode === 'pdf') {
      const page = await browser.newPage();
      await page.goto('file://' + path.resolve(a), { waitUntil: 'load' });
      await page.emulateMedia({ media: 'print' });
      await page.pdf({ path: b, format: 'A4', printBackground: true, preferCSSPageSize: true,
        margin: { top: '20mm', bottom: '20mm', left: '30mm', right: '15mm' } });
    } else if (mode === 'png') {
      const page = await browser.newPage({ deviceScaleFactor: 2 });
      fs.mkdirSync(b, { recursive: true });
      for (const f of fs.readdirSync(a).filter(n => n.endsWith('.svg')).sort()) {
        const svg = fs.readFileSync(path.join(a, f), 'utf8');
        await page.setContent('<!doctype html><html><body style="margin:0;background:#fff">' + svg + '</body></html>');
        const el = await page.$('svg');
        await el.screenshot({ path: path.join(b, f.replace(/\.svg$/, '.png')), timeout: 15000 });
      }
    } else {
      throw new Error('unknown mode ' + mode);
    }
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
