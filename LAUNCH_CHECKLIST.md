# BoringStuff — Checklist Sebelum Rilis

BoringStuff saat ini disiapkan untuk uji coba publik skala kecil dengan satu instance dan penyimpanan persisten. Jangan menganggap aplikasi siap untuk skala besar sebelum pengujian operasional selesai.

## Verifikasi lokal

- [ ] Instal dependensi dari `requirements.txt` pada virtual environment bersih.
- [ ] Jalankan `python -m unittest discover -v` dan pastikan semua pengujian lulus.
- [ ] Jalankan aplikasi dan uji semua 11 kartu alat publik pada desktop dan ponsel.
- [ ] Uji Pembuat Dokumen: buat surat pengunduran diri dan surat lamaran dalam bahasa Indonesia serta Inggris; salin, simpan, ekspor PDF dan DOCX.
- [ ] Uji Asisten Karier AI: analisis CV dan persiapan wawancara dalam kedua bahasa.
- [ ] Uji Peralatan Teks: penghitung kata, pengubah huruf, penghapus duplikasi, pembersih teks, daftar poin, perapih hasil salin, ekstraksi email, dan ekstraksi nomor HP.
- [ ] Uji Patungan & Pajak dengan item yang dibagi rata dan item yang hanya dibagi ke sebagian orang; pastikan total pembagian sama dengan total tagihan.
- [ ] Uji Pembanding Daftar dengan data yang sama, berbeda, dan duplikat.
- [ ] Uji Kalkulator Harga Jual dengan beberapa kombinasi biaya dan margin; pastikan input negatif atau persentase tidak masuk akal ditolak.
- [ ] Uji Teks ke Tabel dan ekspor CSV/XLSX.
- [ ] Uji Foto ke PDF dengan beberapa foto, ubah urutan halaman, dan buka PDF hasilnya.
- [ ] Uji Perapih File Excel/CSV dengan file uji, cek tanggal, nomor HP, nama, baris kosong, duplikasi, dan hasil ekspor.
- [ ] Uji QR Code untuk teks, tautan, WhatsApp, dan Wi-Fi; pindai hasilnya dengan ponsel.
- [ ] Uji Ubah Ukuran & Format Gambar untuk JPG, PNG, dan WebP; pastikan unduhan tunggal dan ZIP dapat dibuka.
- [ ] Uji Perpustakaan: simpan, muat ulang, hapus, restart server, dan uji sesi terpisah di jendela privat.
- [ ] Uji Gemini dengan satu permintaan pada setiap tugas AI. Pastikan error ditampilkan dengan jelas jika API tidak tersedia.
- [ ] Periksa Console browser untuk error JavaScript dan pelanggaran Content Security Policy.
- [ ] Uji layout desktop, ponsel sempit, dan preferensi reduced motion.

## Konfigurasi produksi

- [ ] Gunakan HTTPS melalui platform hosting atau reverse proxy.
- [ ] Set `BORINGSTUFF_ENV=production`.
- [ ] Buat `BORINGSTUFF_SECRET_KEY` unik minimal 32 karakter dan simpan sebagai secret di hosting.
- [ ] Isi `BORINGSTUFF_ALLOWED_HOSTS` hanya dengan hostname resmi.
- [ ] Isi `BORINGSTUFF_PUBLIC_BASE_URL` dengan alamat HTTPS kanonis.
- [ ] Sediakan penyimpanan persisten untuk folder `instance/`.
- [ ] Uji pemulihan backup SQLite.
- [ ] Tambahkan rate limit, perlindungan abuse, dan pemantauan error pada lapisan hosting.
- [ ] Periksa kebijakan privasi, retensi data, dan dependensi CDN eksternal.
- [ ] Pastikan `BORINGSTUFF_LEGACY_TOOLS` tidak diaktifkan. Caption Generator dan PDF Compressor sudah dipensiunkan dari UI publik.
- [ ] Pastikan billing Gemini tidak aktif jika harus menghindari biaya di luar kuota gratis.

## Batasan yang diketahui

- SQLite ditujukan untuk satu instance aplikasi dengan penyimpanan persisten.
- Item Perpustakaan terikat pada cookie sesi browser, bukan akun pengguna. Menghapus cookie dapat membuat item lama tidak dapat diakses.
- Belum tersedia akun pengguna, sinkronisasi lintas perangkat, billing, atau ruang kerja tim.
- Beberapa fitur file memuat pustaka JavaScript dari CDN saat digunakan; koneksi internet diperlukan untuk fitur tersebut.
- Batas permintaan AI aplikasi tidak menggantikan kuota dan batas biaya Google Gemini.

## Keputusan rilis

Jangan mengumumkan aplikasi sebagai layanan publik sebelum backend test suite lulus di lingkungan bersih, smoke test produksi berhasil melalui HTTPS, dan penyimpanan persisten serta pemulihan backup sudah diverifikasi.
