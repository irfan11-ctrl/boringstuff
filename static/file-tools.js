/* BoringStuff file tools: Excel Cleaner, QR Code, Image Resizer. Browser-only. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const toast = (m) => (typeof showToast === "function" ? showToast(m) : null);
  const err = (id, msg) => { const e = $(id); e.textContent = msg || ""; e.hidden = !msg; };
  const download = (name, blob) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  };
  const loaded = {};
  function loadScript(src) {
    if (!loaded[src]) loaded[src] = new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = src; s.onload = res; s.onerror = () => { delete loaded[src]; rej(new Error("Gagal memuat library dari " + new URL(src).host + ". Periksa koneksi internet.")); };
      document.head.appendChild(s);
    });
    return loaded[src];
  }
  const SHEETJS = "https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js";
  const QRLIB = "https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.js";

  /* ---------- Excel cleaner: pure helpers ---------- */
  const MONTHS = { jan: 1, januari: 1, feb: 2, februari: 2, mar: 3, maret: 3, apr: 4, april: 4, mei: 5, may: 5, jun: 6, juni: 6, jul: 7, juli: 7, agu: 8, agt: 8, agustus: 8, aug: 8, sep: 9, sept: 9, september: 9, okt: 10, oktober: 10, oct: 10, nov: 11, november: 11, des: 12, desember: 12, dec: 12 };
  const clean = (v) => String(v ?? "").replace(/[\u00a0\u200b-\u200d\ufeff]/g, " ").replace(/\s+/g, " ").trim();
  function fixName(v) {
    const s = clean(v);
    return s.toLocaleLowerCase("id").replace(/(^|[\s'’-])(\p{L})/gu, (_, p, l) => p + l.toLocaleUpperCase("id"));
  }
  function fixPhone(v, style) {
    const raw = clean(v);
    if (!raw) return raw;
    let d = raw.replace(/[^\d+]/g, "");
    if (d.startsWith("+62")) d = "0" + d.slice(3);
    else if (d.startsWith("62")) d = "0" + d.slice(2);
    else if (d.startsWith("8")) d = "0" + d;
    d = d.replace(/\D/g, "");
    if (!/^08\d{7,12}$/.test(d)) return raw; // not a recognizable mobile number: leave untouched
    return style === "intl" ? "+62" + d.slice(1) : d;
  }
  function fixDate(v, style) {
    const raw = clean(v);
    if (!raw) return raw;
    let y, m, d, x;
    if ((x = raw.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T].*)?$/))) [y, m, d] = [+x[1], +x[2], +x[3]];
    else if ((x = raw.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})(?:[ T].*)?$/))) { [d, m, y] = [+x[1], +x[2], +x[3]]; if (y < 100) y += y > 50 ? 1900 : 2000; }
    else if ((x = raw.match(/^(\d{1,2})\s+([A-Za-z]+)\.?,?\s+(\d{2,4})(?:[ T].*)?$/)) && MONTHS[x[2].toLowerCase()]) { [d, m, y] = [+x[1], MONTHS[x[2].toLowerCase()], +x[3]]; if (y < 100) y += y > 50 ? 1900 : 2000; }
    else return raw;
    const dt = new Date(Date.UTC(y, m - 1, d));
    if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return raw;
    const p = (n) => String(n).padStart(2, "0");
    return style === "dmy" ? `${p(d)}/${p(m)}/${y}` : `${y}-${p(m)}-${p(d)}`;
  }
  function detectKind(header) {
    const h = clean(header).toLowerCase();
    if (/(^|\b)(hp|telp|telepon|phone|wa|whatsapp|mobile|no\.? ?hp)(\b|$)/.test(h)) return "phone";
    if (/(tanggal|tgl|date|lahir|birth)/.test(h)) return "date";
    if (/(nama|name)/.test(h)) return "name";
    return "text";
  }
  function cleanRows(rows, kinds, opts) {
    const stats = { phones: 0, names: 0, dates: 0, duplicates: 0, empty: 0 };
    const seen = new Set(), out = [];
    rows.forEach((row) => {
      const next = row.map((cell, i) => {
        const before = clean(cell);
        let after = before;
        if (kinds[i] === "phone") after = fixPhone(cell, opts.phone);
        else if (kinds[i] === "name") after = fixName(cell);
        else if (kinds[i] === "date") after = fixDate(cell, opts.date);
        if (after !== before) stats[{ phone: "phones", name: "names", date: "dates" }[kinds[i]]]++;
        return after;
      });
      if (next.every((c) => c === "")) { stats.empty++; return; }
      const key = next.join("\u0001").toLowerCase();
      if (opts.dedupe && seen.has(key)) { stats.duplicates++; return; }
      seen.add(key); out.push(next);
    });
    return { rows: out, stats };
  }

  let sheet = { header: [], rows: [] }, cleaned = null, baseName = "data";
  async function onCleanerFile(file) {
    err("cleanError", "");
    $("cleanResult").hidden = true; $("cleanColumns").hidden = true;
    if (!file) return;
    if (file.size > 15 * 1024 * 1024) return err("cleanError", "File terlalu besar (maks. 15 MB).");
    try {
      await loadScript(SHEETJS);
      const wb = XLSX.read(await file.arrayBuffer(), { type: "array", cellDates: false });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const data = XLSX.utils.sheet_to_json(ws, { header: 1, raw: false, defval: "" });
      if (data.length < 2) return err("cleanError", "File kosong atau hanya berisi satu baris.");
      const width = Math.max(...data.map((r) => r.length));
      const pad = (r) => Array.from({ length: width }, (_, i) => r[i] ?? "");
      sheet = { header: pad(data[0]).map((h, i) => clean(h) || `Kolom ${i + 1}`), rows: data.slice(1).map(pad) };
      baseName = file.name.replace(/\.[^.]+$/, "") || "data";
      const box = $("cleanColumnList"); box.replaceChildren();
      sheet.header.forEach((h, i) => {
        const col = document.createElement("div"); col.className = "col-md-6 col-xl-4";
        const lab = document.createElement("label"); lab.className = "form-label"; lab.htmlFor = `cleanKind${i}`; lab.textContent = h;
        const sel = document.createElement("select"); sel.className = "form-select form-select-sm"; sel.id = `cleanKind${i}`;
        [["text", "Teks biasa (rapikan spasi)"], ["name", "Nama (Huruf Kapital Awal)"], ["phone", "Nomor HP"], ["date", "Tanggal"]].forEach(([v, t]) => sel.add(new Option(t, v)));
        sel.value = detectKind(h);
        col.append(lab, sel); box.appendChild(col);
      });
      $("cleanInfo").textContent = `${sheet.rows.length} baris, ${width} kolom terbaca dari sheet "${wb.SheetNames[0]}".`;
      $("cleanColumns").hidden = false;
    } catch (e) { err("cleanError", e.message || "File tidak bisa dibaca."); }
  }
  function runCleaner() {
    const kinds = sheet.header.map((_, i) => $(`cleanKind${i}`).value);
    cleaned = cleanRows(sheet.rows, kinds, { phone: $("cleanPhone").value, date: $("cleanDate").value, dedupe: $("cleanDedupe").checked });
    const s = cleaned.stats;
    $("cleanStats").textContent = `Selesai: ${cleaned.rows.length} baris. Diperbaiki: ${s.phones} nomor HP, ${s.names} nama, ${s.dates} tanggal. Dihapus: ${s.duplicates} baris ganda, ${s.empty} baris kosong.`;
    const t = $("cleanPreview"); t.replaceChildren();
    [sheet.header, ...cleaned.rows.slice(0, 30)].forEach((r, i) => {
      const tr = document.createElement("tr");
      r.forEach((c) => { const el = document.createElement(i ? "td" : "th"); el.textContent = c; tr.appendChild(el); });
      t.appendChild(tr);
    });
    $("cleanResult").hidden = false;
  }
  async function exportXlsx(aoa, filename, sheetName) {
    await loadScript(SHEETJS);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(aoa), sheetName);
    download(filename, new Blob([XLSX.write(wb, { bookType: "xlsx", type: "array" })], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
  }

  /* ---------- QR code ---------- */
  let qrMatrix = null;
  const waNumber = (v) => { let d = String(v).replace(/\D/g, ""); if (d.startsWith("0")) d = "62" + d.slice(1); return d; };
  const wifiEsc = (s) => String(s).replace(/([\\;,:"])/g, "\\$1");
  function qrPayload() {
    const t = $("qrType").value;
    if (t === "wa") {
      const n = waNumber($("qrWaNumber").value);
      if (n.length < 9) throw new Error("Isi nomor WhatsApp yang valid.");
      const m = $("qrWaText").value.trim();
      return `https://wa.me/${n}` + (m ? `?text=${encodeURIComponent(m)}` : "");
    }
    if (t === "wifi") {
      const ssid = $("qrSsid").value;
      if (!ssid) throw new Error("Isi nama WiFi (SSID).");
      const sec = $("qrSec").value;
      return `WIFI:T:${sec};S:${wifiEsc(ssid)};` + (sec === "nopass" ? "" : `P:${wifiEsc($("qrPass").value)};`) + ";";
    }
    const v = $("qrText").value.trim();
    if (!v) throw new Error("Isi teks atau link terlebih dahulu.");
    return v;
  }
  function qrSvg(matrix, color, bg) {
    const n = matrix.length, q = 4, size = n + q * 2;
    let path = "";
    matrix.forEach((row, r) => row.forEach((on, c) => { if (on) path += `M${c + q} ${r + q}h1v1h-1z`; }));
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges"><rect width="${size}" height="${size}" fill="${bg}"/><path d="${path}" fill="${color}"/></svg>`;
  }
  async function runQr() {
    err("qrError", "");
    try {
      const payload = qrPayload();
      await loadScript(QRLIB);
      const qr = qrcode(0, $("qrEc").value);
      qr.addData(payload); qr.make();
      const n = qr.getModuleCount();
      qrMatrix = Array.from({ length: n }, (_, r) => Array.from({ length: n }, (_, c) => qr.isDark(r, c)));
      const holder = $("qrPreview");
      holder.innerHTML = qrSvg(qrMatrix, "#000000", "#ffffff"); // generated locally from a boolean matrix, no user markup
      holder.firstChild.setAttribute("width", "240"); holder.firstChild.setAttribute("height", "240");
      holder.firstChild.setAttribute("role", "img"); holder.firstChild.setAttribute("aria-label", "QR code hasil");
      $("qrResult").hidden = false;
    } catch (e) { $("qrResult").hidden = true; err("qrError", /overflow|length/i.test(e.message) ? "Isi terlalu panjang untuk QR code. Persingkat teks atau turunkan tingkat koreksi." : e.message); }
  }
  function qrToPng() {
    const size = 1024, n = qrMatrix.length + 8, cell = Math.floor(size / n);
    const c = document.createElement("canvas"); c.width = c.height = cell * n;
    const ctx = c.getContext("2d"); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, c.width, c.height); ctx.fillStyle = "#000";
    qrMatrix.forEach((row, r) => row.forEach((on, col) => { if (on) ctx.fillRect((col + 4) * cell, (r + 4) * cell, cell, cell); }));
    return new Promise((res) => c.toBlob(res, "image/png"));
  }
  function qrFields() {
    if (!$("qrType")) return;
    const t = $("qrType").value;
    $("qrFieldText").hidden = t !== "text"; $("qrFieldWa").hidden = t !== "wa"; $("qrFieldWifi").hidden = t !== "wifi";
    $("qrPassWrap").hidden = $("qrSec").value === "nopass";
  }

  /* ---------- Image resizer / converter ---------- */
  let imgFiles = [], imgOut = [];
  const crcTable = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  const crc32 = (b) => { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = crcTable[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  function zipStore(files) { // files: [{name, bytes}], uncompressed ZIP
    const enc = new TextEncoder(), parts = [], central = [];
    let offset = 0;
    const now = new Date(), dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1), dosDate = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
    files.forEach((f) => {
      const name = enc.encode(f.name), crc = crc32(f.bytes);
      const lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true);
      lh.setUint16(10, dosTime, true); lh.setUint16(12, dosDate, true); lh.setUint32(14, crc, true);
      lh.setUint32(18, f.bytes.length, true); lh.setUint32(22, f.bytes.length, true); lh.setUint16(26, name.length, true); lh.setUint16(28, 0, true);
      parts.push(new Uint8Array(lh.buffer), name, f.bytes);
      const ch = new DataView(new ArrayBuffer(46));
      ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true);
      ch.setUint16(12, dosTime, true); ch.setUint16(14, dosDate, true); ch.setUint32(16, crc, true);
      ch.setUint32(20, f.bytes.length, true); ch.setUint32(24, f.bytes.length, true); ch.setUint16(28, name.length, true); ch.setUint32(42, offset, true);
      central.push(new Uint8Array(ch.buffer), name);
      offset += 30 + name.length + f.bytes.length;
    });
    const cdSize = central.reduce((a, b) => a + b.length, 0);
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true); end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
    return new Blob([...parts, ...central, new Uint8Array(end.buffer)], { type: "application/zip" });
  }
  const fmtSize = (b) => (b > 1048576 ? (b / 1048576).toFixed(2) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB");
  async function runImages() {
    err("imgError", "");
    if (!imgFiles.length) return;
    const btn = $("imgRun"); btn.disabled = true; btn.textContent = "Memproses...";
    imgOut = [];
    const list = $("imgOut"); list.replaceChildren();
    const maxW = Math.max(0, parseInt($("imgMax").value, 10) || 0), fmt = $("imgFmt").value, q = parseInt($("imgQ").value, 10) / 100;
    const ext = { "image/webp": "webp", "image/jpeg": "jpg", "image/png": "png" }[fmt], used = new Set();
    let fallback = false;
    try {
      for (const f of imgFiles) {
        let bmp;
        try { bmp = await createImageBitmap(f, { imageOrientation: "from-image" }); } catch (_) { bmp = await createImageBitmap(f); }
        if (bmp.width * bmp.height > 30000000) { if (bmp.close) bmp.close(); throw new Error(`${f.name} melebihi batas 30 megapiksel.`); }
        const scale = maxW && Math.max(bmp.width, bmp.height) > maxW ? maxW / Math.max(bmp.width, bmp.height) : 1;
        const w = Math.max(1, Math.round(bmp.width * scale)), h = Math.max(1, Math.round(bmp.height * scale));
        const c = document.createElement("canvas"); c.width = w; c.height = h;
        const ctx = c.getContext("2d");
        if (fmt === "image/jpeg") { ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h); }
        ctx.drawImage(bmp, 0, 0, w, h); if (bmp.close) bmp.close();
        const blob = await new Promise((r) => c.toBlob(r, fmt, q));
        if (!blob) throw new Error(`Gagal mengubah ${f.name}.`);
        if (blob.type !== fmt) fallback = true;
        let base = f.name.replace(/\.[^.]+$/, "") || "gambar", name = `${base}.${ext}`, i = 2;
        while (used.has(name)) name = `${base}-${i++}.${ext}`;
        used.add(name);
        imgOut.push({ name, blob, from: f.size });
        const li = document.createElement("li"); li.className = "d-flex gap-2 align-items-center py-1";
        const span = document.createElement("span"); span.className = "flex-grow-1 text-truncate"; span.textContent = `${name}: ${fmtSize(f.size)} menjadi ${fmtSize(blob.size)} (${w}×${h})`;
        const b = document.createElement("button"); b.type = "button"; b.className = "btn btn-outline-secondary btn-sm"; b.textContent = "Unduh"; b.setAttribute("aria-label", `Unduh ${name}`);
        b.addEventListener("click", () => download(name, blob));
        li.append(span, b); list.appendChild(li);
      }
      if (fallback) err("imgError", "Browser ini tidak mendukung format yang dipilih untuk sebagian gambar, jadi hasilnya mungkin PNG. Coba format lain atau browser lain.");
      $("imgZip").hidden = imgOut.length < 2; $("imgResult").hidden = false;
    } catch (e) { err("imgError", e.message); }
    finally { btn.disabled = false; btn.textContent = "Proses gambar"; }
  }
  async function zipImages() {
    const files = [];
    for (const o of imgOut) files.push({ name: o.name, bytes: new Uint8Array(await o.blob.arrayBuffer()) });
    download("gambar-boringstuff.zip", zipStore(files));
  }

  /* ---------- wiring ---------- */
  const on = (id, ev, fn) => { const e = $(id); if (e) e.addEventListener(ev, fn); };
  on("cleanFile", "change", (e) => onCleanerFile(e.target.files[0]));
  on("cleanRun", "click", runCleaner);
  on("cleanXlsx", "click", () => cleaned && exportXlsx([sheet.header, ...cleaned.rows], `${baseName}-rapi.xlsx`, "Data").catch((e) => err("cleanError", e.message)));
  on("cleanCsv", "click", () => { if (!cleaned) return; const esc = (c) => (/["\n\r;,]/.test(c) ? `"${c.replace(/"/g, '""')}"` : c); download(`${baseName}-rapi.csv`, new Blob(["\ufeff" + [sheet.header, ...cleaned.rows].map((r) => r.map(esc).join(";")).join("\r\n")], { type: "text/csv;charset=utf-8" })); });
  on("tableXlsx", "click", () => { const rows = window.__boringTableRows; if (rows && rows.length) exportXlsx(rows, "tabel-boringstuff.xlsx", "Data").catch((e) => err("tableError", e.message)); });
  ["qrType", "qrSec"].forEach((id) => on(id, "change", qrFields));
  on("qrRun", "click", runQr);
  on("qrSvg", "click", () => qrMatrix && download("qr-boringstuff.svg", new Blob([qrSvg(qrMatrix, "#000000", "#ffffff")], { type: "image/svg+xml" })));
  on("qrPng", "click", async () => qrMatrix && download("qr-boringstuff.png", await qrToPng()));
  on("imgFiles", "change", (e) => {
    const selected = [...e.target.files];
    const supported = selected.filter((f) => /^image\/(jpeg|png|webp|gif|bmp)$/.test(f.type));
    const sized = supported.filter((f) => f.size > 0 && f.size <= 20 * 1024 * 1024);
    imgFiles = [];
    for (const file of sized.slice(0, 60)) {
      if (imgFiles.reduce((sum, item) => sum + item.size, file.size) > 100 * 1024 * 1024) break;
      imgFiles.push(file);
    }
    let warning = "";
    if (supported.length < selected.length) warning = "Sebagian file dilewati karena format tidak didukung.";
    else if (sized.length < supported.length) warning = "Setiap gambar harus berukuran maksimal 20 MB.";
    else if (imgFiles.length < sized.length) warning = "Batas pemrosesan: 60 gambar dan total 100 MB.";
    err("imgError", warning);
    $("imgCount").textContent = imgFiles.length ? `${imgFiles.length} gambar dipilih.` : "";
    $("imgRun").disabled = !imgFiles.length;
  });
  on("imgQ", "input", () => { $("imgQVal").textContent = $("imgQ").value + "%"; });
  on("imgFmt", "change", () => { $("imgQWrap").hidden = $("imgFmt").value === "image/png"; });
  on("imgRun", "click", runImages);
  on("imgZip", "click", zipImages);
  qrFields();
  window.__boringTest = { fixPhone, fixName, fixDate, cleanRows, zipStore, detectKind };
})();
