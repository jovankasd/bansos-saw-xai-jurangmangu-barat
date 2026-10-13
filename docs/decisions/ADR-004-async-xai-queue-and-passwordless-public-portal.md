# ADR-004: Antrean Worker Asinkron untuk Batch XAI dan Portal Publik Tanpa Akun dengan Proteksi Anti-Bot Dua Lapis

## Status
Accepted

## Date
2026-10-13

## Context
Dua tantangan operasional utama pada sistem ini adalah:
1. **Latensi dan Batas Laju (Rate Limit) Pemanggilan LLM Massal:** Satu periode seleksi melibatkan 100 hingga 300 calon KPM. Memanggil Gemini Flash API secara sinkron di dalam satu siklus HTTP request-response akan memakan waktu puluhan detik hingga menit, memicu *HTTP 504 Gateway Timeout* pada browser staf kelurahan, serta berisiko terkena blokir RPM (*Requests Per Minute*) dari API eksternal.
2. **Aksesibilitas Warga vs Keamanan Data Publik:** Warga pemohon (termasuk lansia) kesulitan jika diwajibkan membuat akun, memverifikasi email, dan mengingat kata sandi hanya untuk mengecek status bansos. Namun, portal publik tanpa login sangat rentan terhadap serangan *brute-force* atau *scraping* untuk menebak status NIK warga lain.

## Decision
1. **Pemrosesan Batch XAI Asinkron (`Django-Q2` / `Celery`):**
   - Endpoint `POST /api/selection/{batch_id}/generate-xai/` tidak mengeksekusi pemanggilan LLM di *main thread*, melainkan mendaftarkan pekerjaan ke *background task queue* dan langsung mengembalikan `HTTP 202 Accepted` beserta `job_id`.
   - Worker memproses kandidat satu per satu dengan pengendali jeda (*rate limiter*), memperbarui progres di basis data, dan secara otomatis mengubah status batch menjadi `Narrated` ketika 100% kandidat selesai diproses.
   - Frontend memantau progres secara *real-time* melalui *polling* ringan ke `GET /api/selection/{batch_id}/xai-progress/`.
2. **Portal Publik Tanpa Login dengan Perisai Verifikasi Ganda & Lockout (`rate_limiter.py`):**
   - Warga cukup memasukkan **16 digit NIK** + **4 digit terakhir Nomor KK** + **CAPTCHA Token** di `/cek-bansos`.
   - Sistem menerapkan pembatasan berlapis menggunakan *Django Cache*:
     1. **IP Rate Limit:** Maksimal 5 *request* per menit per alamat IP.
     2. **Per-NIK Lockout:** Maksimal 5 kegagalan verifikasi (`kk_last4` tidak cocok) berturut-turut pada `nik_hash` yang sama; kegagalan ke-5 mengunci pencarian NIK tersebut selama **15 menit** (`HTTP 429 Too Many Requests`).
   - Hasil seleksi hanya dikembalikan apabila batch berada pada status akhir `Published`, dilengkapi `download_token` bertanda tangan kriptografi (`TimestampSigner`, berlaku 15 menit) untuk mencegah celah IDOR saat mengunduh PDF hasil individu.

## Alternatives Considered

### Alternatif 1: Streaming SSE / WebSockets untuk Progres XAI
- **Pros:** Progres dikirim *push* dari server tanpa *polling*.
- **Cons:** Membutuhkan konfigurasi ASGI/Daphne/Channels tambahan yang memperumit deployment di server kelurahan.
- **Rejected:** *Polling* HTTP ringan setiap 2 detik ke endpoint `/xai-progress/` sudah sangat memadai untuk 1–2 admin kelurahan dan sesuai kontrak PRD Bagian 10.4.

### Alternatif 2: Registrasi Akun Warga dengan OTP WhatsApp/SMS
- **Pros:** Autentikasi kuat per warga.
- **Cons:** Biaya gateway OTP berbayar, friksi tinggi bagi warga lansia, dan di luar ruang lingkup PRD (Bagian 12 Poin 1).
- **Rejected:** Kombinasi 16 digit NIK + 4 digit terakhir KK + CAPTCHA + *15-minute lockout* sudah memberikan keamanan memadai tanpa membebani warga dengan manajemen akun.

## Consequences
- Eksekusi batch 100+ KPM bebas dari *HTTP 504 Timeout*.
- Serangan tebak 4 digit terakhir KK ($10^4$ kombinasi) secara efektif digagalkan oleh *lockout* 15 menit setelah 5 percobaan salah.
