# Phase 15 — Konsistensi Bahasa & Audit Kualitas

## Perubahan
- Menyeragamkan sebagian besar antarmuka, label, tombol, status, dan pesan interaksi menjadi Bahasa Indonesia.
- Mempertahankan opsi bahasa hasil AI (Inggris/Indonesia dan bahasa target terjemahan).
- Memperbaiki penghitung kata agar memakai Intl.Segmenter untuk kata dan grapheme jika didukung browser.
- Memperbaiki Sentence Case agar mengenali awal baris baru.
- Memperbaiki format daftar poin agar tidak menggandakan bullet/nomor yang sudah ada.
- Menolak nama peserta patungan yang duplikat, menghindari penghitungan ganda peserta item, dan memvalidasi persentase layanan/pajak.
- Menambahkan validasi nilai negatif pada kalkulator harga jual.
- Menambahkan batas ukuran dan jumlah foto/gambar serta batas resolusi 30 megapiksel untuk mengurangi risiko kehabisan memori browser.
- Memvalidasi margin Foto ke PDF dan memperketat pengenalan format tanggal Excel agar teks tanggal yang tidak valid tidak ikut diubah.
- Memperbaiki referensi tombol Kosongkan Foto ke PDF yang sebelumnya tidak cocok dengan ID elemen.
- Melokalkan pesan error AI umum dan disclaimer analisis/wawancara saat bahasa Indonesia dipilih.
- Memastikan nilai internal pilihan bahasa terjemahan tetap menggunakan kode yang diterima backend meskipun label tampil dalam Bahasa Indonesia.
- Memperbarui daftar fitur status AI agar tidak lagi mengiklankan Social Caption Generator yang telah dipensiunkan.
- Menulis ulang README agar sesuai dengan fitur aktif, fitur pensiun, privasi, biaya Gemini, dan deployment.

## Catatan audit
- Caption Generator dan PDF Compressor tidak tampil di daftar alat. Endpoint lama tetap ada untuk kompatibilitas, tetapi dinonaktifkan secara default melalui `BORINGSTUFF_LEGACY_TOOLS`.
- Default Gemini `gemini-3.8-flash` tetap dipertahankan; model tersebut tercantum sebagai model stabil pada dokumentasi Gemini API saat revisi ini dibuat.
- Pengujian frontend: 18/18 lulus; pemeriksaan sintaks Python dan JavaScript lulus. Pengujian langsung helper tanggal/nomor HP/Excel, kalkulator patungan/harga jual, arsip ZIP, dan PDF Foto ke PDF juga dilakukan.
- Pengujian backend lengkap perlu dijalankan di lingkungan Windows pengguna dengan `.venv` dan dependensi proyek. Lingkungan audit ini tidak dapat mengunduh dependensi dari internet.
