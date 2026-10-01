// Visual QA of a rendered template, with no business database or login writes.
const fs = require('fs');
const path = require('path');
const http = require('http');
const { chromium } = require(process.env.CODEX_PLAYWRIGHT_PATH || 'playwright');
(async () => {
  const out = path.resolve('output/command_center_qa');
  const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.end(fs.readFileSync(path.join(out, 'index.html')));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({channel:'chrome', headless:true});
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const results = [];
  try {
    for (const width of [1440, 375]) {
      await page.setViewportSize({width, height:900});
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.goto(`http://127.0.0.1:${server.address().port}/`, {waitUntil:'domcontentloaded', timeout:45000});
      await page.getByRole('note').waitFor();
      await page.getByRole('button', {name:'Tạm dừng cập nhật'}).click();
      const paused = await page.getByRole('button', {name:'Tiếp tục cập nhật'}).count();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      await page.screenshot({path:path.join(out, `demo-${width}.png`), fullPage:true});
      results.push({width, paused:paused===1, overflow, errors:[...errors]});
    }
    fs.writeFileSync(path.join(out, 'browser-result.json'), JSON.stringify({scope:'Rendered template only; authorization tested separately',results},null,2));
    console.log(JSON.stringify(results));
    if(results.some(r=>!r.paused || r.overflow || r.errors.length)) process.exitCode=1;
  } finally { await browser.close(); server.close(); }
})().catch(e=>{console.error(e);process.exit(1);});
