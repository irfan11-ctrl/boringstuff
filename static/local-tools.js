/* BoringStuff local tools: Split Bill, List Diff, Margin, Text to Table, Photo to PDF.
   Everything runs in the browser. Nothing is uploaded. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const toast = (m) => (typeof showToast === "function" ? showToast(m) : null);
  const rp = (n) => "Rp" + Math.round(n).toLocaleString("id-ID");
  const num = (v) => { const n = parseFloat(String(v).replace(",", ".")); return Number.isFinite(n) ? n : 0; };

  function download(name, blob) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); }
    catch (_) {
      const t = document.createElement("textarea");
      t.value = text; document.body.appendChild(t); t.select();
      document.execCommand("copy"); t.remove();
    }
    toast("Tersalin ke clipboard.");
  }
  function showError(id, msg) { const e = $(id); e.textContent = msg || ""; e.hidden = !msg; }

  /* ---------- 1. Split Bill ---------- */
  function parsePrice(raw) {
    const s = String(raw || "").toLowerCase().replace(/rp\.?/g, "").replace(/\s+/g, "");
    const m = s.match(/^([\d.,]+)(k|rb|ribu|jt|juta)?$/);
    if (!m) return NaN;
    const mult = { k: 1e3, rb: 1e3, ribu: 1e3, jt: 1e6, juta: 1e6 }[m[2]];
    if (mult) return Math.round(parseFloat(m[1].replace(",", ".")) * mult);
    return parseInt(m[1].replace(/[.,]/g, ""), 10);
  }
  function runSplit() {
    showError("splitError", "");
    const people = $("splitPeople").value.split(/[,\n]/).map((s) => s.trim()).filter(Boolean);
    if (people.length < 2) return showError("splitError", "Isi minimal 2 nama orang, dipisah koma.");
    const lookup = new Map(people.map((p) => [p.toLocaleLowerCase("id-ID"), p]));
    if (lookup.size !== people.length) return showError("splitError", "Nama orang tidak boleh duplikat. Periksa daftar nama.");
    const sub = Object.fromEntries(people.map((p) => [p, 0]));
    let total = 0, count = 0;
    const baris = $("splitItems").value.split("\n").map((l) => l.trim()).filter(Boolean);
    for (const [i, line] of baris.entries()) {
      const parts = line.split("|").map((s) => s.trim());
      const price = parsePrice(parts[1]);
      if (!parts[0] || !(price >= 0)) return showError("splitError", `Baris ${i + 1} tidak valid: "${line}". Format: Nama item | harga | siapa saja (opsional).`);
      let who = people;
      if (parts[2]) {
        who = [];
        const assigned = parts[2].split(/[,;]/).map((s) => s.trim()).filter(Boolean);
        if (!assigned.length) return showError("splitError", `Baris ${i + 1}: daftar nama pembagi tidak valid.`);
        for (const n of assigned) {
          const hit = lookup.get(n.toLocaleLowerCase("id-ID"));
          if (!hit) return showError("splitError", `Baris ${i + 1}: nama "${n}" tidak ada di daftar orang.`);
          if (!who.includes(hit)) who.push(hit);
        }
      }
      who.forEach((p) => (sub[p] += price / who.length));
      total += price; count++;
    }
    if (!count) return showError("splitError", "Isi minimal satu item.");
    const svcPct = num($("splitService").value), taxPct = num($("splitTax").value);
    if (![svcPct, taxPct].every(Number.isFinite) || svcPct < 0 || taxPct < 0 || svcPct > 100 || taxPct > 100 || svcPct + taxPct > 100) {
      return showError("splitError", "Persentase layanan dan pajak harus 0–100%, serta jumlah keduanya tidak boleh melebihi 100%.");
    }
    const svc = total * svcPct / 100;
    const tax = ($("splitTaxAfterService").checked ? total + svc : total) * taxPct / 100;
    const grand = total + svc + tax;
    const share = {};
    people.forEach((p) => (share[p] = Math.round(total ? sub[p] + (sub[p] / total) * (svc + tax) : 0)));
    const diff = Math.round(grand) - people.reduce((a, p) => a + share[p], 0);
    if (diff) { const top = people.reduce((a, b) => (share[a] >= share[b] ? a : b)); share[top] += diff; }
    let out = `*Patungan*\nSubtotal: ${rp(total)}\n`;
    if (svcPct) out += `Service ${svcPct}%: ${rp(svc)}\n`;
    if (taxPct) out += `Pajak ${taxPct}%: ${rp(tax)}\n`;
    out += `*Total: ${rp(grand)}*\n\n`;
    people.forEach((p) => (out += `${p}: ${rp(share[p])}\n`));
    $("splitOutput").value = out.trim();
    $("splitResult").hidden = false;
  }

  /* ---------- 2. List Diff ---------- */
  function runDiff() {
    const ci = $("diffCase").checked;
    const norm = (s) => { const t = s.trim().replace(/\s+/g, " "); return ci ? t.toLowerCase() : t; };
    const read = (id) => $(id).value.split("\n").map((l) => l.trim()).filter(Boolean);
    const A = read("diffA"), B = read("diffB");
    const mapOf = (arr) => { const m = new Map(), dup = new Set(); arr.forEach((x) => { const k = norm(x); if (m.has(k)) dup.add(m.get(k)); else m.set(k, x); }); return { m, dup }; };
    const a = mapOf(A), b = mapOf(B);
    const onlyA = [...a.m].filter(([k]) => !b.m.has(k)).map(([, v]) => v);
    const onlyB = [...b.m].filter(([k]) => !a.m.has(k)).map(([, v]) => v);
    const both = [...a.m].filter(([k]) => b.m.has(k)).map(([, v]) => v);
    const sections = [
      ["Hanya di Daftar A", onlyA], ["Hanya di Daftar B", onlyB], ["Ada di keduanya", both],
      ["Ganda di Daftar A", [...a.dup]], ["Ganda di Daftar B", [...b.dup]],
    ];
    const box = $("diffResult");
    box.replaceChildren();
    sections.forEach(([title, items]) => {
      const col = document.createElement("div");
      col.className = "col-md-6 col-xl-4";
      const h = document.createElement("div");
      h.className = "form-label";
      h.textContent = `${title} (${items.length})`;
      const t = document.createElement("textarea");
      t.className = "form-control"; t.rows = 6; t.readOnly = true; t.value = items.join("\n");
      t.setAttribute("aria-label", title);
      const btn = document.createElement("button");
      btn.type = "button"; btn.className = "btn btn-outline-secondary btn-sm mt-2"; btn.textContent = "Salin";
      btn.addEventListener("click", () => copy(t.value));
      col.append(h, t, btn);
      box.appendChild(col);
    });
    box.hidden = false;
  }

  /* ---------- 3. Margin calculator ---------- */
  function runMargin() {
    showError("marginError", "");
    const cost = num($("mCost").value), fixed = num($("mFixed").value);
    const feePct = num($("mFee").value) + num($("mProgram").value) + num($("mPromo").value);
    const target = num($("mTarget").value);
    const denom = 1 - (feePct + target) / 100;
    if (cost <= 0) return showError("marginError", "Isi modal (HPP) lebih dari 0.");
    if (fixed < 0 || feePct < 0 || target < 0) return showError("marginError", "Biaya tetap, potongan, dan target margin tidak boleh negatif.");
    if (feePct > 100 || target > 100 || denom <= 0) return showError("marginError", "Total potongan dan target margin harus kurang dari 100%. Periksa kembali persentasenya.");
    const price = Math.ceil((cost + fixed) / denom / 100) * 100;
    const fees = price * feePct / 100 + fixed;
    const profit = price - cost - fees;
    const rows = [
      ["Harga jual yang disarankan", rp(price)], ["Total potongan marketplace", rp(fees) + ` (${feePct}% + biaya tetap)`],
      ["Modal (HPP)", rp(cost)], ["Untung bersih per item", rp(profit)],
      ["Margin dari harga jual", (price ? (profit / price) * 100 : 0).toFixed(1) + "%"],
      ["Markup dari modal", ((profit / cost) * 100).toFixed(1) + "%"],
    ];
    const tb = $("marginRows");
    tb.replaceChildren();
    rows.forEach(([k, v]) => { const tr = document.createElement("tr"); const a = document.createElement("td"), b = document.createElement("td"); a.textContent = k; b.textContent = v; b.className = "text-end fw-semibold"; tr.append(a, b); tb.appendChild(tr); });
    $("marginResult").hidden = false;
  }

  /* ---------- 4. Text to Table ---------- */
  let tableRows = [];
  const WA_PREFIX = /^\[?\d{1,2}[\/.]\d{1,2}[\/.]\d{2,4},?\s*\d{1,2}[.:]\d{2}(?:[.:]\d{2})?\]?\s*-?\s*/;
  function splitLines(baris, mode) {
    const cands = { tab: "\t", pipe: "|", semi: ";", comma: ",", dash: " - ", colon: ":" };
    let sep = cands[mode];
    if (mode === "auto") {
      sep = ["\t", "|", ";", " - ", ","].find((s) => baris.filter((l) => l.includes(s)).length >= Math.max(1, baris.length * 0.6)) || null;
    }
    if (!sep) return baris.map((l) => (/\s{2,}/.test(l) ? l.split(/\s{2,}/) : [l]));
    return baris.map((l) => l.split(sep));
  }
  function runTable() {
    showError("tableError", "");
    let baris = $("tableInput").value.split("\n").map((l) => l.trim()).filter(Boolean);
    if (!baris.length) return showError("tableError", "Tempel teks dulu.");
    if ($("tableStripWa").checked) baris = baris.map((l) => l.replace(WA_PREFIX, "")).filter(Boolean);
    let rows = splitLines(baris, $("tableDelim").value).map((r) => r.map((c) => c.trim()));
    const cols = Math.max(...rows.map((r) => r.length));
    rows = rows.map((r) => r.concat(Array(cols - r.length).fill("")));
    if (!$("tableHeader").checked) rows.unshift(Array.from({ length: cols }, (_, i) => `Kolom ${i + 1}`));
    tableRows = rows;
    window.__boringTableRows = rows;
    const table = $("tablePreview");
    table.replaceChildren();
    rows.slice(0, 201).forEach((r, i) => {
      const tr = document.createElement("tr");
      r.forEach((c) => { const cell = document.createElement(i === 0 ? "th" : "td"); cell.textContent = c; tr.appendChild(cell); });
      table.appendChild(tr);
    });
    $("tableInfo").textContent = `${rows.length - 1} baris data × ${cols} kolom` + (rows.length > 201 ? " (pratinjau 200 baris pertama, unduhan berisi semua)" : "");
    $("tableResult").hidden = false;
  }
  function downloadCsv(sep) {
    if (!tableRows.length) return;
    const esc = (c) => (/["\n\r;,]/.test(c) ? `"${c.replace(/"/g, '""')}"` : c);
    const csv = "\ufeff" + tableRows.map((r) => r.map(esc).join(sep)).join("\r\n");
    download("tabel-boringstuff.csv", new Blob([csv], { type: "text/csv;charset=utf-8" }));
  }

  /* ---------- 5. Photo to PDF ---------- */
  let photos = [];
  function renderPhotos() {
    const list = $("photoList");
    list.replaceChildren();
    photos.forEach((f, i) => {
      const li = document.createElement("li");
      li.className = "d-flex align-items-center gap-2 py-1";
      const name = document.createElement("span");
      name.className = "flex-grow-1 text-truncate";
      name.textContent = `${i + 1}. ${f.name} (${(f.size / 1024).toFixed(0)} KB)`;
      const mk = (label, aria, fn, disabled) => { const b = document.createElement("button"); b.type = "button"; b.className = "btn btn-outline-secondary btn-sm"; b.textContent = label; b.setAttribute("aria-label", `${aria} ${f.name}`); b.disabled = disabled; b.addEventListener("click", fn); return b; };
      li.append(name,
        mk("↑", "Naikkan", () => { [photos[i - 1], photos[i]] = [photos[i], photos[i - 1]]; renderPhotos(); }, i === 0),
        mk("↓", "Turunkan", () => { [photos[i + 1], photos[i]] = [photos[i], photos[i + 1]]; renderPhotos(); }, i === photos.length - 1),
        mk("✕", "Hapus", () => { photos.splice(i, 1); renderPhotos(); }, false));
      list.appendChild(li);
    });
    $("photoBuild").disabled = !photos.length;
  }
  async function toJpeg(file) {
    let bmp;
    try { bmp = await createImageBitmap(file, { imageOrientation: "from-image" }); }
    catch (_) { bmp = await createImageBitmap(file); }
    if (bmp.width * bmp.height > 30000000) { if (bmp.close) bmp.close(); throw new Error("Foto melebihi batas 30 megapiksel."); }
    const scale = Math.min(1, 2400 / Math.max(bmp.width, bmp.height));
    const w = Math.max(1, Math.round(bmp.width * scale)), h = Math.max(1, Math.round(bmp.height * scale));
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
    ctx.drawImage(bmp, 0, 0, w, h);
    if (bmp.close) bmp.close();
    const blob = await new Promise((res) => c.toBlob(res, "image/jpeg", 0.85));
    if (!blob) throw new Error("Gagal mengubah gambar.");
    return { bytes: new Uint8Array(await blob.arrayBuffer()), w, h };
  }
  function buildPdf(images, mode, margin) {
    const enc = new TextEncoder(), chunks = [], offsets = [];
    let len = 0;
    const push = (x) => { const b = typeof x === "string" ? enc.encode(x) : x; chunks.push(b); len += b.length; };
    const obj = (n, body) => { offsets[n] = len; push(`${n} 0 obj\n`); push(body); push("\nendobj\n"); };
    const f = (n) => n.toFixed(2);
    push("%PDF-1.4\n%\xe2\xe3\xcf\xd3\n");
    obj(1, "<</Type/Catalog/Pages 2 0 R>>");
    obj(2, `<</Type/Pages/Count ${images.length}/Kids[${images.map((_, i) => `${3 + 3 * i} 0 R`).join(" ")}]>>`);
    images.forEach((im, i) => {
      const p = 3 + 3 * i;
      let pw, ph, x, y, w, h;
      if (mode === "a4") {
        [pw, ph] = im.w > im.h ? [841.89, 595.28] : [595.28, 841.89];
        const s = Math.min((pw - 2 * margin) / im.w, (ph - 2 * margin) / im.h);
        w = im.w * s; h = im.h * s; x = (pw - w) / 2; y = (ph - h) / 2;
      } else { pw = w = im.w * 0.75; ph = h = im.h * 0.75; x = y = 0; }
      const content = `q ${f(w)} 0 0 ${f(h)} ${f(x)} ${f(y)} cm /Im0 Do Q`;
      obj(p, `<</Type/Page/Parent 2 0 R/MediaBox[0 0 ${f(pw)} ${f(ph)}]/Resources<</XObject<</Im0 ${p + 2} 0 R>>>>/Contents ${p + 1} 0 R>>`);
      obj(p + 1, `<</Length ${content.length}>>\nstream\n${content}\nendstream`);
      offsets[p + 2] = len;
      push(`${p + 2} 0 obj\n<</Type/XObject/Subtype/Image/Width ${im.w}/Height ${im.h}/ColorSpace/DeviceRGB/BitsPerComponent 8/Filter/DCTDecode/Length ${im.bytes.length}>>\nstream\n`);
      push(im.bytes); push("\nendstream\nendobj\n");
    });
    const total = 3 + 3 * images.length, xref = len;
    let x = `xref\n0 ${total}\n0000000000 65535 f \n`;
    for (let n = 1; n < total; n++) x += String(offsets[n]).padStart(10, "0") + " 00000 n \n";
    push(x + `trailer\n<</Size ${total}/Root 1 0 R>>\nstartxref\n${xref}\n%%EOF`);
    return new Blob(chunks, { type: "application/pdf" });
  }
  async function runPhotoPdf() {
    showError("photoError", "");
    const btn = $("photoBuild");
    btn.disabled = true; btn.textContent = "Memproses...";
    try {
      if (!photos.length) throw new Error("Pilih minimal satu foto terlebih dahulu.");
      const margin = Number($("photoMargin").value);
      if (!Number.isFinite(margin) || margin < 0 || margin > 100) {
        throw new Error("Margin A4 harus antara 0 dan 100 pt.");
      }
      const images = [];
      for (const f of photos) images.push(await toJpeg(f));
      download("dokumen-boringstuff.pdf", buildPdf(images, $("photoMode").value, margin));
      toast("PDF selesai dibuat di perangkat Anda.");
    } catch (e) {
      showError("photoError", "Gagal membuat PDF: " + (e.message || "format gambar tidak didukung browser ini."));
    } finally { btn.textContent = "Buat PDF"; btn.disabled = !photos.length; }
  }
  function addPhotos(fileList) {
    const candidates = [...fileList];
    const supported = candidates.filter((f) => /^image\/(jpeg|png|webp|gif|bmp)$/.test(f.type));
    const withinLimit = supported.filter((f) => f.size > 0 && f.size <= 20 * 1024 * 1024);
    const combined = photos.concat(withinLimit).slice(0, 40);
    const totalBytes = combined.reduce((sum, file) => sum + file.size, 0);
    if (supported.length < candidates.length) showError("photoError", "Sebagian file dilewati. Format yang didukung: JPG, PNG, WebP, GIF, dan BMP.");
    else if (withinLimit.length < supported.length) showError("photoError", "Setiap foto harus berukuran maksimal 20 MB dan tidak boleh kosong.");
    else if (combined.length < photos.length + withinLimit.length) showError("photoError", "Maksimal 40 foto dapat digabungkan dalam satu PDF.");
    else if (totalBytes > 100 * 1024 * 1024) showError("photoError", "Total ukuran foto maksimal 100 MB agar browser tetap stabil.");
    else showError("photoError", "");
    if (totalBytes <= 100 * 1024 * 1024) photos = combined;
    renderPhotos();
  }

  /* ---------- wiring ---------- */
  const on = (id, ev, fn) => { const e = $(id); if (e) e.addEventListener(ev, fn); };
  on("splitRun", "click", runSplit);
  on("splitCopy", "click", () => copy($("splitOutput").value));
  on("diffRun", "click", runDiff);
  on("marginRun", "click", runMargin);
  on("tableRun", "click", runTable);
  on("tableCsvId", "click", () => downloadCsv(";"));
  on("tableCsvSheets", "click", () => downloadCsv(","));
  on("photoFiles", "change", (e) => { addPhotos(e.target.files); e.target.value = ""; });
  on("photoBuild", "click", runPhotoPdf);
  on("photoClear", "click", () => { photos = []; renderPhotos(); showError("photoError", ""); });
})();
