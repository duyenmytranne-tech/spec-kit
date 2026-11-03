// Nghiệm thu bằng mô phỏng người dùng (Playwright + Chromium) cho SR783 và báo cáo.
//   node acceptance/simulate_users.cjs
// Ghi acceptance/report.json và ảnh chụp acceptance/screenshots/*.png; mã thoát 1 nếu có lỗi.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const os = require('os');

const ROOT = path.resolve(__dirname, '..');
const APP = 'file://' + path.join(ROOT, 'app', 'sr783-standalone.html');
const REPORT_HTML = 'file://' + path.join(ROOT, 'report', 'BAO-CAO-7.83Hz.html');
const SHOTS = path.join(__dirname, 'screenshots');
const results = JSON.parse(fs.readFileSync(path.join(ROOT, 'results', 'results.json'), 'utf8'));
const bench = JSON.parse(fs.readFileSync(path.join(__dirname, 'benchmark_vi.json'), 'utf8'));
const checks = [];
const metrics = {};
const check = (persona, name, pass, detail) => { checks.push({ persona, name, pass: !!pass, detail: detail ?? null });
  console.log(`${pass ? 'PASS' : 'FAIL'}  [${persona}] ${name}${detail !== undefined ? '  ' + JSON.stringify(detail) : ''}`); };
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sr783-acc-'));

// ---- minimal PNG decoder (8-bit RGB/RGBA, non-interlaced) for flash measurement ----
function decodePng(buf) {
  let pos = 8, w = 0, h = 0, ct = 0; const idat = [];
  while (pos < buf.length) { const len = buf.readUInt32BE(pos), type = buf.toString('ascii', pos + 4, pos + 8), data = buf.subarray(pos + 8, pos + 8 + len);
    if (type === 'IHDR') { w = data.readUInt32BE(0); h = data.readUInt32BE(4); ct = data[9]; } else if (type === 'IDAT') idat.push(data); else if (type === 'IEND') break; pos += 12 + len; }
  const bpp = ct === 6 ? 4 : 3, raw = zlib.inflateSync(Buffer.concat(idat)), stride = w * bpp, out = Buffer.alloc(h * stride);
  for (let y = 0; y < h; y++) { const f = raw[y * (stride + 1)], line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    for (let x = 0; x < stride; x++) { const a = x >= bpp ? out[y * stride + x - bpp] : 0, b = y ? out[(y - 1) * stride + x] : 0, c = x >= bpp && y ? out[(y - 1) * stride + x - bpp] : 0;
      let v = line[x]; if (f === 1) v += a; else if (f === 2) v += b; else if (f === 3) v += (a + b) >> 1;
      else if (f === 4) { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); v += pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
      out[y * stride + x] = v & 255; } }
  return { w, h, bpp, px: out };
}
const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
function tileLuminance(img, cols = 6, rows = 4) {
  const out = []; for (let ty = 0; ty < rows; ty++) for (let tx = 0; tx < cols; tx++) { let s = 0, n = 0;
    for (let y = Math.floor(ty * img.h / rows); y < Math.floor((ty + 1) * img.h / rows); y += 2) for (let x = Math.floor(tx * img.w / cols); x < Math.floor((tx + 1) * img.w / cols); x += 2) {
      const i = (y * img.w + x) * img.bpp; s += 0.2126 * lin(img.px[i]) + 0.7152 * lin(img.px[i + 1]) + 0.0722 * lin(img.px[i + 2]); n++; }
    out.push(s / n); } return out;
}

async function botCount(page) { return page.$$eval('.msg.bot', els => els.length); }
async function ask(page, text) {
  const before = await botCount(page); await page.fill('#chat-input', text); await page.press('#chat-input', 'Enter');
  await page.waitForFunction((n) => document.querySelectorAll('.msg.bot').length > n, before, { timeout: 5000 });
  return page.$eval('.msg.bot:last-of-type', el => ({ text: el.querySelector('.body').textContent, grade: (el.querySelector('.grade') || {}).textContent || null }));
}

(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  try {
    // ---------------- P6: Kỹ sư phần mềm – đối chiếu bit Python ↔ JavaScript ----------------
    {
      const page = await browser.newPage(); const errors = [];
      page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      await page.goto(APP); await page.waitForTimeout(500);
      const par = await page.evaluate((res) => {
        const c = window.SR783.core, out = [], pq = c.toRational('7,83'); const ie = c.ieee(7.83), b = res.bits.ieee754;
        out.push(['ieee.hex32', ie.hex32 === b.binary32.hex], ['ieee.hex64', ie.hex64 === b.binary64.hex],
          ['ieee.exact32', ie.exact32 === b.binary32.exact_value], ['ieee.exact64', ie.exact64 === b.binary64.exact_value]);
        res.synth.dds.forEach(d => { const j = c.dds(pq.p, pq.q, d.f_clk_hz, d.accumulator_bits); out.push([`dds.${d.accumulator_bits}bit.${d.f_clk_hz}`, j.word.toString() === String(d.tuning_word) && j.fout === d.f_out_hz]); });
        const t = c.timer1(pq.p, pq.q), tb = res.synth.timer1;
        out.push(['timer1', t.ocr === tb.best.ocr && t.fout === tb.best.f_out_hz && t.ppm === tb.best.error_ppm && t.TCCR1B === tb.registers.TCCR1B]);
        res.synth.phase_vectors.forEach((v, i) => { const u = c.phaseUnits(BigInt(v.p), BigInt(v.q), v.t_ms, v.t0_ms);
          out.push([`phase.${i}`, u.num.toString() === String(v.phase_num) && u.mod.toString() === String(v.phase_mod) && c.phaseDeg(BigInt(v.p), BigInt(v.q), v.t_ms, v.t0_ms) === v.phase_deg]); });
        const s72 = res.secded.binary64_secded_72_64, s22 = res.secded.ocr1a_secded_22_16;
        out.push(['secded72', c.SECDED72.hex(c.SECDED72.encode(BigInt(s72.data_hex))) === s72.codeword_hex.slice(2)]);
        out.push(['secded22', c.SECDED22.hex(c.SECDED22.encode(BigInt(s22.data_hex))) === s22.codeword_hex.slice(2)]);
        res.secded.bcd_783_secded_8_4.forEach(x => out.push([`secded8.${x.digit}`, c.SECDED8.encode(BigInt(parseInt(x.digit))).toString(2).padStart(8, '0') === x.codeword_bits]));
        const f = res.settings_record.fields, pk = c.packSettings({ p: BigInt(f.p), q: BigInt(f.q), carrierCenti: f.carrier_centi_hz, volume: f.volume_pct, mode: 'I', minutes: f.session_min, flags: f.flags });
        out.push(['settings_record', pk.cw.join() === res.settings_record.codewords.join() && pk.tag === res.settings_record.tag]);
        out.push(['sync_code', c.syncCode(783n, 100n, '1793664000000', 'I') === res.synth.sync_code_example.code]);
        let prev = c.GENESIS; res.integrity.chain_entries.forEach((e, i) => { prev = c.chainNext(prev, e); out.push([`chain.${i}`, prev === res.integrity.chain_hashes[i]]); });
        const g = c.splitmix64(0); out.push(['splitmix64', res.prng.splitmix64_seed0.every(h => '0x' + g.next().toString(16).toUpperCase().padStart(16, '0') === h)]);
        out.push(['sha256', c.sha256('abc') === res.integrity.sha256_abc && c.sha256('') === res.integrity.sha256_empty]);
        return { out, kbHash: c.sha256(document.getElementById('sr783-kb').textContent) };
      }, results);
      par.out.forEach(([n, ok]) => check('P6 đối chiếu bit', n, ok));
      metrics.parity_checks = par.out.length;
      const kbHash = crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT, 'kb', 'kb_vi.json'))).digest('hex');
      check('P6 đối chiếu bit', 'kb_sha256_js_eq_node', par.kbHash === kbHash, kbHash.slice(0, 16));
      // WAV: Python CLI vs JavaScript synthesis, sample by sample
      const pyWav = path.join(tmp, 'py.wav');
      execFileSync('python3', ['-m', 'sr783', 'tone', '--mode', 'isochronic', '--seconds', '0.5', '--out', pyWav], { cwd: ROOT });
      const js = Buffer.from(await page.evaluate(() => Array.from(window.SR783.core.synthWav(783n, 100n, 'I', 0.5, 48000, 200, 0.3, 3))));
      const py = fs.readFileSync(pyWav); let diff = 0, maxd = 0;
      for (let i = 44; i < Math.min(js.length, py.length); i += 2) { const d = Math.abs(js.readInt16LE(i) - py.readInt16LE(i)); if (d) diff++; maxd = Math.max(maxd, d); }
      metrics.wav_samples_compared = (py.length - 44) / 2; metrics.wav_samples_differing = diff; metrics.wav_max_lsb_diff = maxd;
      check('P6 đối chiếu bit', 'wav_python_eq_js', js.length === py.length && js.subarray(0, 44).equals(py.subarray(0, 44)) && maxd <= 1, { diff, maxd, bytes: py.length });
      check('P6 đối chiếu bit', 'no_console_errors', errors.length === 0, errors);
      await page.close();
    }

    // ---------------- P1: Người dùng phổ thông (điện thoại) ----------------
    {
      const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } }); const page = await ctx.newPage();
      await page.goto(APP); await page.waitForTimeout(400);
      let ok = 0; const miss = [];
      const r1 = await ask(page, '7,83 Hz là gì?');
      check('P1 người dùng', 'hoi_7_83_la_gi', /cộng hưởng Schumann/.test(r1.text) && /A$/.test(r1.grade || ''), r1.grade);
      const r2 = await ask(page, 'tan so schumann dang tang len 40 hz?');
      check('P1 người dùng', 'tin_don_tang_tan_so_bac_bo', /Không có bằng chứng/.test(r2.text) && /D$/.test(r2.grade || ''), r2.grade);
      const r3 = await ask(page, 'máy phát 7,83 Hz có tác dụng không');
      check('P1 người dùng', 'may_phat_co_muc_bang_chung', /máy phát|Máy phát/.test(r3.text) && !!r3.grade, r3.grade);
      const r4 = await ask(page, 'bắt đầu đẳng thời 1 phút'); await page.waitForTimeout(400);
      const playing = await page.$eval('#play-state', el => el.textContent);
      check('P1 người dùng', 'lenh_bat_dau', playing === 'Đang phát' && /1 phút/.test(r4.text), playing);
      const ac = await page.evaluate(() => ({ playing: window.SR783.state.playing, mode: window.SR783.state.mode }));
      check('P1 người dùng', 'trang_thai_phien', ac.playing === true && ac.mode === 'I', ac);
      await ask(page, 'dừng'); await page.waitForTimeout(300);
      check('P1 người dùng', 'lenh_dung', (await page.$eval('#play-state', el => el.textContent)) === 'Đang dừng');
      const r5 = await ask(page, 'tôi muốn tự tử');
      check('P1 người dùng', 'khung_hoang_co_115', /115/.test(r5.text));
      await page.screenshot({ path: path.join(SHOTS, 'app_mobile.png') });
      // full benchmark through the same engine the UI uses
      const b = await page.evaluate((bench) => { const S = window.SR783; let ok = 0; const miss = [];
        for (const [q, exp] of bench.questions) { const it = S.parseCommand(q) ? null : S.matchIntent(q); if (it && it.id === exp) ok++; else miss.push([q, exp, it && it.id]); }
        const crisis = bench.crisis.filter(q => (S.parseCommand(q) || {}).type === 'crisis').length;
        const medical = bench.medical.filter(q => (S.parseCommand(q) || {}).type === 'medical').length;
        const cmds = bench.commands.filter(([q, exp]) => { const c = S.parseCommand(q) || {}; return Object.keys(exp).every(k => c[k] === exp[k]); }).length;
        const notc = bench.not_commands.filter(q => S.parseCommand(q) === null).length;
        return { ok, total: bench.questions.length, miss, crisis, medical, cmds, notc }; }, bench);
      metrics.benchmark = b;
      check('P1 người dùng', 'benchmark_chu_de_>=90%', b.ok / b.total >= 0.9, `${b.ok}/${b.total}`);
      check('P1 người dùng', 'benchmark_khung_hoang_100%', b.crisis === bench.crisis.length, `${b.crisis}/${bench.crisis.length}`);
      check('P1 người dùng', 'benchmark_y_te_100%', b.medical === bench.medical.length, `${b.medical}/${bench.medical.length}`);
      check('P1 người dùng', 'benchmark_lenh_100%', b.cmds === bench.commands.length, `${b.cmds}/${bench.commands.length}`);
      check('P1 người dùng', 'cau_hoi_khong_thanh_lenh', b.notc === bench.not_commands.length, `${b.notc}/${bench.not_commands.length}`);
      await page.setViewportSize({ width: 360, height: 800 }); await page.waitForTimeout(200);
      const sw = await page.evaluate(() => document.documentElement.scrollWidth);
      metrics.scroll_width_at_360 = sw; check('P1 người dùng', 'khong_cuon_ngang_360px', sw <= 360, sw);
      await ctx.close();
    }

    // ---------------- P2: Nhóm đồng bộ hai thiết bị (đồng hồ B lệch +3 ms) ----------------
    {
      const ctxA = await browser.newContext({ viewport: { width: 1280, height: 900 } });
      const ctxB = await browser.newContext({ viewport: { width: 1280, height: 900 } });
      await ctxB.addInitScript(() => { const now = Date.now; Date.now = () => now() + 3; });
      const A = await ctxA.newPage(), B = await ctxB.newPage();
      await A.goto(APP); await B.goto(APP); await A.waitForTimeout(400);
      await A.click('#make-code'); const code = (await A.$eval('#code-out', el => el.textContent)).trim();
      check('P2 đồng bộ', 'tao_ma_phien', /^SR783-1-783-100-\d+-I-[0-9A-F]{8}$/.test(code), code);
      await B.fill('#join-code', code); await B.click('#join'); await B.waitForTimeout(200);
      const joined = await B.$eval('.msg.bot:last-of-type .body', el => el.textContent);
      check('P2 đồng bộ', 'tham_gia_ma_phien', /Đã tham gia phiên/.test(joined));
      const sA = await A.evaluate(() => ({ p: String(window.SR783.state.p), q: String(window.SR783.state.q), t0: window.SR783.state.t0, mode: window.SR783.state.mode }));
      const sB = await B.evaluate(() => ({ p: String(window.SR783.state.p), q: String(window.SR783.state.q), t0: window.SR783.state.t0, mode: window.SR783.state.mode }));
      check('P2 đồng bộ', 'tham_so_trung_nhau', JSON.stringify(sA) === JSON.stringify(sB), sA);
      const T = 1793664012345;
      const uA = await A.evaluate((t) => { const s = window.SR783.state, u = window.SR783.core.phaseUnits(s.p, s.q, t, s.t0); return u.num + '/' + u.mod; }, T);
      const uB = await B.evaluate((t) => { const s = window.SR783.state, u = window.SR783.core.phaseUnits(s.p, s.q, t, s.t0); return u.num + '/' + u.mod; }, T);
      check('P2 đồng bộ', 'pha_trung_tuyet_doi_cung_thoi_diem', uA === uB, uA);
      // phase each device believes it has, referred to one common real-time instant
      // phase each device computes from its own (offset) clock, referred to one common real-time instant;
      // repeated 20 times: SC-003 requires < 10 degrees in at least 95 % of measurements
      const probe = () => { const S = window.SR783, s = S.state, real = performance.timeOrigin + performance.now();
        const u = S.core.phaseUnitsUs(s.p, s.q, S.clock.nowUs(), s.t0); return { cyc: Number(u.num) / Number(u.mod), real, f: Number(s.p) / Number(s.q) }; };
      const diffs = [];
      for (let k = 0; k < 20; k++) { const [pa, pb] = await Promise.all([A.evaluate(probe), B.evaluate(probe)]);
        const ref = Math.max(pa.real, pb.real), at = (p) => ((p.cyc + p.f * (ref - p.real) / 1000) % 1 + 1) % 1;
        let d = (at(pb) - at(pa)) * 360; d = ((d + 540) % 360) - 180; diffs.push(d); await A.waitForTimeout(25); }
      const within = diffs.filter(d => Math.abs(d) < 10).length, mean = diffs.reduce((a, b) => a + b, 0) / diffs.length;
      metrics.two_device_phase = { offset_ms: 3, expected_deg: 8.46, mean_deg: Number(mean.toFixed(2)), max_abs_deg: Number(Math.max(...diffs.map(Math.abs)).toFixed(2)), within_10deg: `${within}/${diffs.length}` };
      check('P2 đồng bộ', 'lech_pha_<10do_khi_lech_dong_ho_3ms_>=95%', within / diffs.length >= 0.95, metrics.two_device_phase);
      check('P2 đồng bộ', 'do_lech_pha_khop_ly_thuyet_360fδ', Math.abs(mean - 8.46) < 1.5, Number(mean.toFixed(2)));
      const bad = code.slice(0, -1) + (code.endsWith('0') ? '1' : '0');
      await B.fill('#join-code', bad); await B.click('#join'); await B.waitForTimeout(200);
      const rej = await B.$eval('.msg.bot:last-of-type .body', el => el.textContent);
      check('P2 đồng bộ', 'tu_choi_ma_sai', /Sai mã kiểm tra SHA-256/.test(rej));
      await A.screenshot({ path: path.join(SHOTS, 'app_desktop.png'), fullPage: true });
      await ctxA.close(); await ctxB.close();
    }

    // ---------------- P3: Kỹ sư kiểm định thiết bị ----------------
    {
      const page = await browser.newPage({ viewport: { width: 1280, height: 900 } }); await page.goto(APP); await page.waitForTimeout(300);
      await page.click('#tab-verify'); await page.click('#v-sample'); await page.waitForTimeout(500);
      const out = await page.$eval('#v-out', el => el.textContent);
      const m = /Tần số đo: ([0-9]+,[0-9]+) Hz/.exec(out); const fm = m ? Number(m[1].replace(',', '.')) : NaN;
      metrics.verify_sample_f_hz = fm;
      check('P3 kiểm định', 'du_lieu_mau_7_85Hz_sai_<=0_01', Math.abs(fm - 7.85) <= 0.01, fm);
      check('P3 kiểm định', 'ket_luan_dat', /^Đạt/.test(out), out.slice(0, 40));
      await page.screenshot({ path: path.join(SHOTS, 'app_verify.png'), fullPage: false });
      let seed = 12345; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
      const rows = ['time_s,field_uT']; for (let i = 0; i < 3000; i++) rows.push((i / 100).toFixed(2) + ',' + (45 + (rnd() - 0.5)).toFixed(3));
      const noise = path.join(tmp, 'noise.csv'); fs.writeFileSync(noise, rows.join('\n'));
      await page.setInputFiles('#v-file', noise); await page.waitForTimeout(500);
      const out2 = await page.$eval('#v-out', el => el.textContent);
      check('P3 kiểm định', 'nhieu_thuan_khong_xac_dinh', /Không xác định/.test(out2), out2.slice(0, 50));
      await page.click('#tab-sr');
      const sr = path.join(tmp, 'sr.csv'); fs.writeFileSync(sr, 'time_utc,f1_hz,quality\n2026-11-03T08:00:00Z,7.801,good\n2026-11-03T08:10:00Z,7.792,good\n2026-11-03T08:20:00Z,9.600,poor\n');
      await page.setInputFiles('#sr-file', sr); await page.waitForTimeout(300);
      check('P3 kiểm định', 'csv_schumann_chon_dong_hop_le', (await page.$eval('#sr-f', el => el.value)) === '7,792');
      await page.click('#sr-apply'); await page.waitForTimeout(100);
      const pq = await page.evaluate(() => String(window.SR783.state.p) + '/' + String(window.SR783.state.q));
      check('P3 kiểm định', 'dong_bo_theo_schumann_thuc_do_974_125', pq === '974/125', pq);
      await page.fill('#sr-f', '9,6'); await page.click('#sr-apply');
      check('P3 kiểm định', 'tu_choi_ngoai_dai', /ngoài dải/.test(await page.$eval('#sr-out', el => el.textContent)));
      await page.close();
    }

    // ---------------- P4: Kiểm thử độ bền (tự sửa lỗi) ----------------
    {
      const page = await browser.newPage({ viewport: { width: 1280, height: 900 } }); await page.goto(APP); await page.waitForTimeout(300);
      const fi = await page.evaluate(() => { const S = window.SR783; const key = 'sr783.settings.v1';
        localStorage.removeItem(key); S.loadSettings(); const original = localStorage.getItem(key);
        let single = 0, singleOk = 0, dbl = 0, dblOk = 0;
        for (let w = 0; w < 2; w++) for (let b = 0; b < 72; b++) { localStorage.setItem(key, original); S.flipStored(1, w, b); const r = S.loadSettings(); single++;
          if (r.status === 'corrected' && localStorage.getItem(key) === original) singleOk++; }
        for (let k = 0; k < 400; k++) { localStorage.setItem(key, original); const w = k % 2, b1 = (k * 7) % 72, b2 = (b1 + 1 + (k * 13) % 71) % 72;
          S.flipStored(2, w, b1, b2); const r = S.loadSettings(); dbl++; if (r.status === 'restored') dblOk++; }
        localStorage.setItem(key, original); S.loadSettings();
        return { single, singleOk, dbl, dblOk }; });
      metrics.fault_injection_app = fi;
      check('P4 độ bền', 'lat_1_bit_moi_vi_tri_tu_sua_100%', fi.single === 144 && fi.singleOk === 144, fi);
      check('P4 độ bền', 'lat_2_bit_phat_hien_100%', fi.dblOk === fi.dbl, fi);
      await page.click('#tab-int'); await page.click('#i-flip1'); await page.waitForTimeout(100);
      check('P4 độ bền', 'giao_dien_lat_1_bit', /tự sửa/.test(await page.$eval('#i-out', el => el.textContent)));
      await page.click('#i-flip2'); await page.waitForTimeout(100);
      check('P4 độ bền', 'giao_dien_lat_2_bit', /lỗi 2 bit/.test(await page.$eval('#i-out', el => el.textContent)));
      await page.click('#i-verify');
      check('P4 độ bền', 'chuoi_bam_hop_le', /Chuỗi băm hợp lệ/.test(await page.$eval('#i-out', el => el.textContent)));
      await page.screenshot({ path: path.join(SHOTS, 'app_integrity.png'), fullPage: false });
      await page.evaluate(() => { window.SR783.state.log[0].entry.mode = 'X'; });
      await page.click('#i-verify');
      check('P4 độ bền', 'chuoi_bam_phat_hien_sua_doi', /KHÔNG hợp lệ/.test(await page.$eval('#i-out', el => el.textContent)));
      await page.close();
    }

    // ---------------- P5: Người nhạy cảm ánh sáng (đo nhấp nháy theo khung hình) ----------------
    {
      // small viewport so that capture runs above the Nyquist rate of a 7.83 Hz flash (> 15.66 frames/s)
      const ctx = await browser.newContext({ viewport: { width: 480, height: 360 } }); const page = await ctx.newPage();
      await page.goto(APP); await page.waitForTimeout(300); await page.click('#start'); await page.click('#breath-toggle');
      await page.evaluate(() => document.getElementById('dial').scrollIntoView({ block: 'center' })); await page.waitForTimeout(300);
      // compositor screencast: one PNG per repaint (the phase needle repaints every animation frame)
      const cdp = await ctx.newCDPSession(page); const raw = [];
      cdp.on('Page.screencastFrame', (ev) => { raw.push({ t: ev.metadata.timestamp * 1000, png: Buffer.from(ev.data, 'base64') });
        cdp.send('Page.screencastFrameAck', { sessionId: ev.sessionId }).catch(() => {}); });
      await cdp.send('Page.startScreencast', { format: 'png', maxWidth: 480, maxHeight: 360, everyNthFrame: 1 });
      await page.waitForTimeout(4000); await cdp.send('Page.stopScreencast');
      const tStart = raw.length ? raw[0].t : 0;
      const frames = raw.map(r => ({ t: r.t - tStart, lum: tileLuminance(decodePng(r.png), 4, 3) }));
      const tiles = frames[0].lum.length; let worst = 0, maxDelta = 0;
      for (let k = 0; k < tiles; k++) { const series = frames.map(f => ({ t: f.t, L: f.lum[k] })); const trans = [];
        for (let i = 1; i < series.length; i++) { const d = Math.abs(series[i].L - series[i - 1].L); maxDelta = Math.max(maxDelta, d);
          if (d >= 0.1 && Math.min(series[i].L, series[i - 1].L) < 0.8) trans.push(series[i].t); }
        for (const ts of trans) { const n = trans.filter(x => x >= ts && x < ts + 1000).length / 2; worst = Math.max(worst, n); } }
      const fps = frames.length / ((frames[frames.length - 1].t) / 1000);
      metrics.flash = { frames: frames.length, fps: Number(fps.toFixed(1)), nyquist_ok_for_7_83Hz: fps > 2 * 7.83, tiles,
        max_tile_luminance_step: Number(maxDelta.toFixed(4)), max_flashes_per_second: worst };
      check('P5 nhạy cảm ánh sáng', 'lay_mau_tren_nguong_nyquist', fps > 2 * 7.83, Number(fps.toFixed(1)));
      check('P5 nhạy cảm ánh sáng', 'khong_qua_3_lan_nhap_nhay_moi_giay', worst <= 3, metrics.flash);
      await page.click('#stop'); await page.click('#breath-toggle');
      await page.emulateMedia({ colorScheme: 'dark' }); await page.waitForTimeout(200);
      const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      check('P5 nhạy cảm ánh sáng', 'giao_dien_toi_dung_token', bg === 'rgb(11, 15, 29)', bg);
      await page.screenshot({ path: path.join(SHOTS, 'app_dark.png'), fullPage: false });
      await ctx.close();
    }

    // ---------------- P7: Người đọc báo cáo ----------------
    {
      const page = await browser.newPage({ viewport: { width: 1100, height: 900 } }); await page.goto(REPORT_HTML); await page.waitForTimeout(500);
      const r = await page.evaluate(() => { const links = [...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href').slice(1));
        const broken = links.filter(id => !document.getElementById(id)); const imgs = [...document.images];
        return { links: links.length, broken, images: imgs.length, notLoaded: imgs.filter(i => !(i.complete && i.naturalWidth > 0)).length,
          h1: document.querySelectorAll('h1').length, tables: document.querySelectorAll('table').length }; });
      metrics.report_html = r;
      check('P7 người đọc', 'lien_ket_noi_bo_khong_gay', r.links > 0 && r.broken.length === 0, r.broken);
      check('P7 người đọc', 'hinh_tai_du_9', r.images === 9 && r.notLoaded === 0, r);
      await page.screenshot({ path: path.join(SHOTS, 'report_first_screen.png') });
      await page.close();
    }
  } finally { await browser.close(); }

  const passed = checks.filter(c => c.pass).length;
  const report = { generated_utc: new Date().toISOString(), summary: { total: checks.length, passed, failed: checks.length - passed }, metrics, checks };
  fs.writeFileSync(path.join(__dirname, 'report.json'), JSON.stringify(report, null, 1) + '\n');
  console.log(`\nTỔNG: ${passed}/${checks.length} đạt`);
  process.exit(passed === checks.length ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
