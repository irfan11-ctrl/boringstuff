# Mengaktifkan Gemini AI di BoringStuff (Windows)

1. Buka folder project.
2. Salin `.env.example`, lalu ubah nama salinannya menjadi `.env`.
3. Buka `.env` dengan Notepad dan masukkan kunci API Gemini pada `GEMINI_API_KEY`.
4. Simpan file dan mulai ulang Flask.
5. Periksa status AI pada aplikasi, lalu jalankan setidaknya satu tugas AI. Status kunci terdeteksi belum membuktikan bahwa kunci, model, kuota, dan akses API benar-benar berfungsi.

```powershell
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Jika virtual environment belum tersedia:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Menghindari biaya tak terduga

Gunakan project Google AI Studio pada kuota gratis dan biarkan billing berbayar tidak aktif jika kamu harus memastikan tidak ada pengeluaran. Kuota gratis, akses model, dan batas permintaan dapat berubah. BoringStuff membatasi permintaan per sesi browser dan alamat IP; batas Google tetap berlaku secara terpisah.

## Data dan privasi

Kunci Gemini hanya dibaca backend Flask dari `.env`, tidak ditaruh di JavaScript browser, dan tidak dikembalikan oleh `/api/ai/status`. Teks yang dimasukkan ke Pembuat Dokumen, Asisten Karier AI, dan Asisten Penulisan Gemini dikirim ke Google Gemini untuk diproses. Jangan masukkan kata sandi, nomor identitas, alamat rumah, atau informasi rahasia. Gunakan CV yang sudah disamarkan.

Peralatan Teks, Patungan, Pembanding Daftar, Kalkulator Harga Jual, Teks ke Tabel, Foto ke PDF, Perapih File Excel, QR Code, dan Ubah Ukuran Gambar berjalan di browser. Beberapa fitur memuat pustaka dari CDN, tetapi konten yang sedang diproses tidak dikirim ke backend aplikasi.
