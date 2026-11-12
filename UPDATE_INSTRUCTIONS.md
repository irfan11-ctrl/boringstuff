# Memperbarui BoringStuff ke Phase 15

Pembaruan ini dibuat dari arsip `boringstuff_siap_deploy.zip` yang kamu kirim. Pembaruan mempertahankan Pembuat Dokumen, Asisten Karier AI, semua alat lokal, Perpustakaan, tautan Trakteer dan Buy Me a Coffee, SEO, keamanan, serta konfigurasi deployment.

## Windows

1. Hentikan Flask dengan `Ctrl+C`.
2. Ekstrak ZIP Phase 15 ke folder sementara.
3. Salin isi folder `boringstuff` ke folder project yang sedang digunakan dan pilih **Replace** untuk file yang sama.
4. Jangan hapus atau timpa `.env`, `.venv`, atau `instance/`. Ketiganya tidak disertakan dalam ZIP.
5. Jalankan pengujian lengkap lalu mulai ulang aplikasi.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe app.py
```

Tidak ada migrasi database untuk pembaruan ini. Caption Generator dan PDF Compressor tidak ditampilkan di UI dan endpoint lamanya tetap nonaktif secara default. Jangan set `BORINGSTUFF_LEGACY_TOOLS=1` pada hosting publik.
