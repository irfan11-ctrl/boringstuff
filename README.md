# BoringStuff

**Alat kecil. Tugas repetitif. Selesai dalam hitungan detik.**

BoringStuff adalah kumpulan utilitas ringan untuk pekerjaan sehari-hari. Antarmuka utama menggunakan Bahasa Indonesia. Beberapa alat AI dapat menghasilkan teks dalam bahasa pilihan pengguna.

## Fitur yang tersedia

### Utilitas lokal — teks tidak dikirim ke server

- **Patungan & Pajak:** membagi biaya per orang, termasuk pajak dan biaya layanan. Setiap item dapat dibagi ke orang tertentu.
- **Pembanding Daftar:** mencari item yang hanya ada di daftar A/B, item yang sama, dan duplikasi.
- **Kalkulator Harga Jual:** menghitung harga jual berdasarkan HPP, biaya tetap, potongan, dan target margin.
- **Teks ke Tabel:** memecah teks per baris menjadi kolom dan mengekspor CSV/XLSX.
- **Foto ke PDF:** menggabungkan foto menjadi PDF langsung di browser.
- **Perapih File Excel/CSV:** membersihkan spasi, nama, nomor HP, tanggal, baris kosong, dan duplikasi; ekspor ke CSV/XLSX.
- **QR Code:** membuat QR teks/link, WhatsApp, atau Wi-Fi.
- **Pengecil Gambar & WebP:** mengubah ukuran/format gambar dan mengunduh hasil secara ZIP.
- **Peralatan Teks:** penghitung kata/karakter, pengubah huruf, penghapus baris duplikat, pembersih teks, daftar poin, perapih teks hasil salin, ekstraksi email, dan ekstraksi nomor HP.

Utilitas lokal diproses di browser. File tidak dikirim ke backend aplikasi. Beberapa pustaka untuk membaca/mengekspor spreadsheet dan membuat QR dimuat dari CDN saat fitur digunakan; koneksi internet diperlukan untuk bagian tersebut.

### Fitur Gemini AI

- Pembuat Dokumen: surat pengunduran diri dan surat lamaran.
- Asisten Karier AI: analisis CV terhadap deskripsi lowongan dan persiapan wawancara.
- Asisten Penulisan: tulis ulang teks, balasan email, ringkasan, perbaikan tata bahasa, terjemahan, pesan sopan, dan rumus Excel/Google Sheets.

Fitur AI memerlukan `GEMINI_API_KEY`. Teks yang dimasukkan ke fitur AI dikirim ke Google Gemini untuk diproses. Jangan masukkan kata sandi, data identitas sensitif, atau informasi rahasia. Periksa setiap hasil AI sebelum digunakan. Jika Gemini tidak tersedia, aplikasi menampilkan pesan kesalahan dan tidak menyajikan template lokal seolah-olah hasil AI.

**Catatan biaya:** kuota gratis dan ketentuan Google dapat berubah. Untuk menghindari tagihan tak terduga, periksa pengaturan billing di Google AI Studio/Google Cloud dan jangan mengaktifkan billing berbayar kecuali memang disetujui. Batas aplikasi saat ini adalah 20 permintaan AI per sesi browser per jam dan 60 permintaan per alamat IP per jam; batas Google tetap berlaku terpisah.

## Fitur yang sudah dipensiunkan

Social Caption Generator dan PDF Compressor tidak ditampilkan pada antarmuka publik. Endpoint backend lama tetap dipertahankan untuk kompatibilitas pengujian, tetapi dinonaktifkan secara default. Jangan mengaktifkan `BORINGSTUFF_LEGACY_TOOLS=1` pada deployment publik.

## Menjalankan di Windows

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py
```

Buka `http://127.0.0.1:5000`.

Masukkan kunci Gemini hanya di file `.env`:

```env
GEMINI_API_KEY=isi_kunci_di_lokal
GEMINI_MODEL=gemini-3.8-flash
```

Jangan pernah mengirim kunci API ke chat, menaruhnya di HTML/JavaScript, atau memasukkannya ke Git. Model default `gemini-3.8-flash` adalah nama model stabil yang tercantum dalam dokumentasi Gemini API saat revisi ini dibuat; ketersediaan dan kebijakan model dapat berubah.

## Pengujian

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Pengujian frontend tidak membutuhkan dependensi Flask. Pengujian backend membutuhkan paket pada `requirements.txt`.

## Konfigurasi deployment

Aplikasi menyediakan `wsgi.py` dan `Procfile`. Untuk mode produksi, siapkan variabel lingkungan berikut:

```powershell
$env:BORINGSTUFF_ENV = "production"
$env:BORINGSTUFF_SECRET_KEY = (py -c "import secrets; print(secrets.token_urlsafe(48))")
$env:BORINGSTUFF_ALLOWED_HOSTS = "contoh.com,www.contoh.com"
$env:BORINGSTUFF_PUBLIC_BASE_URL = "https://www.contoh.com"
```

Jalankan melalui server WSGI (Waitress tersedia untuk Windows) di belakang platform/proxy HTTPS. Jangan mengekspos server pengembangan Flask langsung ke internet.

**Penyimpanan persisten wajib:** folder `instance/` berisi database SQLite dan rahasia sesi lokal. Gunakan volume persisten dan buat cadangan berkala. Jangan menjalankan beberapa replika aplikasi yang berbagi file SQLite biasa.

## Privasi dan keamanan

- Cookie sesi menggunakan HttpOnly dan SameSite=Lax; Secure aktif pada mode produksi.
- Header keamanan dan Content Security Policy disetel oleh backend.
- API tidak diindeks melalui `robots.txt`; sitemap memerlukan `BORINGSTUFF_PUBLIC_BASE_URL`.
- Library disimpan pada SQLite dan terikat pada cookie sesi browser. Menghapus cookie dapat membuat item lama tidak dapat diakses.
- Utilitas lokal berjalan di browser, tetapi file library eksternal yang dibutuhkan beberapa alat dimuat dari CDN versi tetap.
- Aplikasi belum menyediakan akun pengguna, sinkronisasi Library lintas perangkat, atau pembatasan trafik terdistribusi. Tambahkan rate limit dan perlindungan abuse pada lapisan hosting sebelum trafik publik ditingkatkan.

## Dukungan

Pengguna dapat mendukung pengembangan melalui tautan Trakteer dan Buy Me a Coffee yang tersedia pada situs.
