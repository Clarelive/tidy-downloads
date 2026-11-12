// 出片：用无头浏览器逐帧截图，再交给 ffmpeg。
// 用法：node render.js <scene.html> <输出目录> [--stills 0,30,90] [--scale 0.5] [--range 240,540] [--cover 封面.png]
// scene.html 要提供 window.ready（Promise，返回 {frames,fps,w,h,sfx}）和 window.draw(frame)。
const {chromium} = require('playwright');
const path = require('path'), fs = require('fs'), http = require('http');

(async () => {
  const [scene, outDir] = process.argv.slice(2);
  const arg = k => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
  const stills = arg('--stills'), scale = parseFloat(arg('--scale') || '1');
  const root = path.resolve(__dirname, '..');
  // 起一个只读的本地小服务，让页面能 fetch 同目录的数据
  const mime = {'.html': 'text/html', '.json': 'application/json', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.js': 'text/javascript'};
  const srv = http.createServer((q, s) => {
    const f = path.join(root, decodeURIComponent(q.url.split('?')[0]));
    if (!f.startsWith(root) || !fs.existsSync(f)) { s.writeHead(404); return s.end(); }
    s.writeHead(200, {'content-type': mime[path.extname(f)] || 'application/octet-stream'}); fs.createReadStream(f).pipe(s);
  }).listen(0);
  const url = `http://127.0.0.1:${srv.address().port}/` + path.relative(root, path.resolve(scene)).split(path.sep).map(encodeURIComponent).join('/');
  fs.mkdirSync(outDir, {recursive: true});
  const browser = await chromium.launch();
  const open = async () => {
    const p = await browser.newPage({viewport: {width: 1080, height: 1920}, deviceScaleFactor: scale});
    p.on('pageerror', e => { console.error('PAGE ERROR', e.message); process.exitCode = 1; });
    await p.goto(url); const meta = await p.evaluate(() => window.ready); return [p, meta];
  };
  if (arg('--cover')) {   // 单独出一张封面：页面要提供 window.drawCover()
    const [p] = await open(); await p.evaluate(() => window.drawCover()); await p.screenshot({path: arg('--cover')});
  } else if (stills) {
    const [p, meta] = await open();
    for (const f of stills.split(',').map(Number)) { await p.evaluate(n => window.draw(n), f); await p.screenshot({path: path.join(outDir, `still_${String(f).padStart(5, '0')}.png`)}); }
    fs.writeFileSync(path.join(outDir, 'meta.json'), JSON.stringify(meta));
  } else {
    const NP = 4; let meta;
    await Promise.all([...Array(NP)].map(async (_, k) => {
      const [p, m] = await open(); meta = m;
      const [fa, fb] = (arg('--range') || `0,${m.frames - 1}`).split(',').map(Number);   // --range 起,止：只重出这一段
      for (let f = fa + k; f <= Math.min(fb, m.frames - 1); f += NP) { await p.evaluate(n => window.draw(n), f); await p.screenshot({path: path.join(outDir, `f_${String(f).padStart(5, '0')}.png`)}); }
    }));
    fs.writeFileSync(path.join(outDir, 'meta.json'), JSON.stringify(meta));
    console.log('frames', meta.frames);
  }
  await browser.close(); srv.close();
})();
