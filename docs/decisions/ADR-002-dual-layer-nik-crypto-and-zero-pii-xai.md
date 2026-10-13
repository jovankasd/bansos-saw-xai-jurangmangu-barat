# ADR-002: Proteksi Kriptografi Dua Lapis untuk NIK (AES-256-GCM + HMAC-SHA256) dan Sanitasi Zero-PII ke API Eksternal

## Status
Accepted

## Date
2026-10-13

## Context
Sistem memproses Nomor Induk Kependudukan (NIK 16 digit) dan Nomor Kartu Keluarga (KK) warga Kelurahan Jurangmangu Barat. Berdasarkan **UU No. 27 Tahun 2022 tentang Perlindungan Data Pribadi (UU PDP)**, NIK merupakan data pribadi spesifik/sensitif yang:
1. Tidak boleh disimpan dalam bentuk teks terbuka (*plaintext*) di dalam basis data maupun *log* aplikasi.
2. Harus tetap dapat dicari secara cepat ($O(1)$ *index lookup*) ketika warga melakukan pengecekan status di Portal Publik `/cek-bansos` atau saat sistem mendeteksi duplikasi NIK pada unggahan Excel RT.
3. Harus dapat didekripsi kembali **hanya** ketika kelurahan mencetak dokumen hukum resmi (PDF Berita Acara Penetapan KPM).
4. **Dilarang keras** dikirimkan ke layanan pihak ketiga eksternal (Google Gemini API).

## Decision
Kami menerapkan arsitektur privasi tiga komponen di `backend/core/crypto.py` dan `backend/core/services/sanitizer.py`:
1. **Enkripsi At-Rest (`nik_encrypted`) dengan AES-256-GCM:**
   Setiap NIK dienkripsi menggunakan kunci simetris 256-bit (`NIK_AES_KEY` dari *environment variable*) dengan *nonce* acak 96-bit per *record*. Format simpan berupa `base64(nonce || ciphertext || tag)`.
2. **Blind Indexing (`nik_hash`) dengan HMAC-SHA256 Ber-Pepper:**
   Karena AES-256-GCM bersifat *probabilistic* (enkripsi NIK yang sama menghasilkan *ciphertext* berbeda), pencarian cepat dan constraint `UNIQUE` dilakukan pada kolom `nik_hash` yang dihitung dengan `HMAC-SHA256(key=NIK_HMAC_PEPPER, msg=raw_nik)`. Penggunaan *server-side pepper* mencegah serangan *rainbow table* pada ruang angka 16 digit NIK.
3. **Masking Visual (`nik_masked`) & Sanitasi Zero-PII (`sanitizer.py`):**
   - Kolom `nik_masked` menyimpan format `367403******0002` untuk tampilan antarmuka sehari-hari tanpa perlu memanggil fungsi dekripsi.
   - `build_anonymous_payload()` membuang seluruh atribut tabel `CITIZEN` (`full_name`, `nik_encrypted`, `nik_masked`, `kk_last4`, `address`) dan hanya mengirim kode anonim `KPM-{evaluation_id:03d}` beserta vektor skor ke Gemini API.

## Alternatives Considered

### Alternatif 1: Hashing Satu Arah Saja (bcrypt / Argon2 / SHA-256 tanpa AES)
- **Pros:** NIK tidak mungkin didekripsi meskipun kunci bocor.
- **Cons:** Bcrypt/Argon2 terlalu lambat untuk pencarian `WHERE nik_hash = ...` dan deteksi duplikasi ratusan baris Excel; além itu, hashing satu arah membuat kelurahan tidak bisa mencetak NIK lengkap pada lampiran resmi Berita Acara (FR-07).
- **Rejected:** Tidak memenuhi kebutuhan pelaporan resmi kelurahan (FR-07) dan performa pencarian.

### Alternatif 2: Enkripsi Deterministik (AES-ECB atau Nonce Statis)
- **Pros:** Satu kolom bisa dipakai untuk enkripsi sekaligus pencarian `UNIQUE`.
- **Cons:** Rentan terhadap analisis pola (*chosen-plaintext / pattern leakage*) dan tidak memenuhi standar praktik terbaik kriptografi modern.
- **Rejected:** Memisahkan `nik_encrypted` (AES-256-GCM dengan *random nonce*) dan `nik_hash` (HMAC-SHA256) memberikan jaminan kerahasiaan (*semantic security*) sekaligus autentikasi integritas.

## Consequences
- Basis data tidak pernah menyimpan NIK *plaintext*; kebocoran *dump* tabel SQLite/PostgreSQL tanpa *environment variables* (`NIK_AES_KEY` dan `NIK_HMAC_PEPPER`) tidak mengungkap NIK warga.
- Pencarian warga di `/api/public/check-status/` dan pengecekan duplikat Excel berjalan dalam waktu konstan melalui indeks `UNIQUE` pada `nik_hash`.
- Fungsi `decrypt_nik()` hanya dipanggil di dalam `pdf_generator.py` saat pembuatan Berita Acara resmi dan wajib dicatat ke tabel `AUDIT_LOG`.
