# AGENTS.md — Context & Rules: Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Bansos Jurangmangu Barat

Dokumen ini adalah **Level 1 Context Rules** (persistent project rules) berdasarkan `PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md` dan arahan arsitektur UI/UX pengguna. Seluruh agen AI wajib mematuhi aturan di bawah ini pada setiap sesi.

---

## 1. Tech Stack & Arsitektur Utama
- **Frontend:** React.js (Vite), Tailwind CSS (Design System: *Civic Precision* — `Hanken Grotesk` & `JetBrains Mono`, palet Emerald Civic `#003426` / `#0f4c3a`).
- **Backend:** Python, Django 5.x, Django REST Framework (DRF), SimpleJWT (untuk autentikasi staf).
- **Database:** SQLite (Development) / PostgreSQL (Production).
- **Async Task Queue:** Django-Q atau Celery + Redis (untuk pemrosesan batch XAI Gemini).
- **AI Explainer:** Google Gemini Flash API (`temperature: 0.15`, `response_mime_type: "application/json"`) + `deterministic_fallback.py` (rule-based).
- **Kriptografi (UU PDP No. 27/2022):** `AES-256-GCM` (enkripsi NIK *at-rest* di `nik_encrypted`) + `HMAC-SHA256` dengan server-side pepper (indexing pencarian cepat di `nik_hash`).
- **Reporting:** ReportLab / WeasyPrint (PDF Berita Acara + QR Code + Lampiran TMS) & `openpyxl` (Import/Export Excel).

---

## 2. Protokol Wajib Implementasi Desain (`.stitch`) & Responsivitas
Folder `.stitch/designs/` berisi 6 referensi desain awal (*Civic Precision*), namun **tampilannya saat ini masih belum rapi, beberapa elemen terpotong (clipped), tidak responsif untuk Tablet/Mobile, dan memiliki beberapa deviasi dari PRD**.

### Aturan Keras UI/UX (JANGAN LANGSUNG ASAL TERAPKAN):
1. **Wajib Review Sebelum Implementasi Layar:**
   - **DILARANG** menyalin mentah-mentah (*copy-paste* buta) kode HTML dari `.stitch/designs/*.html` ke komponen React.
   - Setiap kali akan mulai mengimplementasikan suatu halaman/komponen UI, agen **WAJIB melakukan review desain terlebih dahulu bersama pengguna**: paparkan apa yang diambil dari `.stitch`, bagian mana yang dirapikan/diperbaiki, dan tunggu persetujuan pengguna.
2. **Wajib Responsif Penuh di 3 Ukuran Layar (Mobile, Tablet, Desktop):**
   - **Mobile / Handphone (`< 768px` / `base` - `sm`):**
     - Sidebar **TIDAK BOLEH** `fixed w-64` permanen yang menutupi layar. Gunakan *Off-Canvas Slide-Over Drawer* dengan tombol *Hamburger Menu* di Topbar.
     - Grid kartu metrik dan layout utama wajib menumpuk vertikal (`grid-cols-1`), padding proporsional (`px-4`), dan tombol aksi mudah disentuh (min tinggi `40px`–`44px`).
     - Tabel padat (seperti matriks SAW $R_{ij}$ dan ranking) harus memiliki *wrapper* `overflow-x-auto` yang rapi dengan kolom identitas tetap terbaca atau opsi tampilan kartu ringkas (*card stack*) di layar sempit.
   - **Tablet (`768px – 1023px` / `md`):**
     - Sidebar berupa *drawer* atau *collapsible icon rail*, grid metrik `md:grid-cols-2`, form dan panel master-detail ditata bertingkat agar tidak ada teks/angka yang terjepit.
   - **Desktop / Browser (`>= 1024px` / `lg` - `xl`):**
     - Sidebar `lg:fixed lg:w-64`, konten utama `lg:pl-64`, grid `lg:grid-cols-12`.
     - Topbar harus menggunakan `flex-wrap` atau pengelompokan yang bersih agar *badge*, *dropdown batch*, dan profil pengguna **tidak pernah terpotong (clipped)** di tepi kanan layar.
3. **Koreksi Inkonsistensi `.stitch` terhadap PRD:**
   - **Kriteria $C_1 - C_4$ harus seragam di semua layar:** $C_1$ Pendapatan Keluarga (Cost, 0.30), $C_2$ Jumlah Tanggungan (Benefit, 0.25), $C_3$ Kondisi Tempat Tinggal (Cost, 0.25), $C_4$ Kepemilikan Aset (Cost, 0.20). *(Jangan gunakan "Daya Listrik 900 VA" untuk $C_4$ seperti di sebagian file `.stitch`)*.
   - **Menu Sidebar harus konsisten dan sesuai RBAC (Bagian 3 PRD):** Role `Viewer` (Lurah) tidak boleh melihat tombol eksekusi mutasi seperti "Eksekusi Batch SAW".
   - **Patuhi Batasan "Not Doing" (Bagian 12 PRD):** Jangan buat form upload sanggahan dua arah di Portal Publik (arahkan warga melapor ke Ketua RT untuk pemutakhiran periode berikutnya) dan jangan buat fitur sinkronisasi langsung ke API SIKS-NG/DTKS Kemensos.

---

## 3. Aturan Bisnis & Algoritma Inti (Berdasarkan PRD Final v3.0)
1. **Validasi & Pembekuan Kriteria (FR-01):**
   - Kalkulasi SAW wajib ditolak jika $\sum w_j \neq 1.00$.
   - Saat kalkulasi dimulai, bekukan bobot ke tabel `BATCH_CRITERIA` agar perubahan bobot di masa depan tidak merusak histori batch lama.
2. **Filter TMS (FR-02):**
   - Warga berstatus `DISQUALIFIED` (ASN/TNI/Polri, PKH Ganda, Pindah, Meninggal) dikecualikan dari matriks normalisasi SAW (tidak boleh mendistorsi $\min/\max$ kriteria), namun tetap disimpan untuk lampiran Berita Acara.
3. **SAW Engine & Hierarchical Tie-Breaker (FR-03):**
   - Benefit: $r_{ij} = \frac{x_{ij}}{\max_i x_{ij}}$, Cost: $r_{ij} = \frac{\min_i x_{ij}}{x_{ij}}$, Preferensi: $V_i = \sum_{j=1}^n w_j r_{ij}$.
   - Jika terdapat skor $V_i$ kembar di batas kuota, selesaikan secara deterministik bertingkat:
     1. Nilai normalisasi $r_{i, C_1}$ terbesar,
     2. Nilai normalisasi $r_{i, C_2}$ terbesar,
     3. Jumlah tanggungan riil terbesar,
     4. Timestamp pengusulan (`created_at`) paling awal.
4. **Zero-PII XAI & Fallback Deterministik (FR-04, FR-05):**
   - **DILARANG KERAS** mengirim nama asli, NIK, No KK, atau alamat ke Gemini API. Hanya kirim `applicant_code` (mis. `KPM-042`), `rank`, `quota`, `status`, `final_score`, `cutoff_score`, dan `criteria_data` ($r_{ij}$, $w_j$, rata-rata lolos $\bar{r}_j^{\text{lolos}}$).
   - Jika Gemini API gagal setelah 2x retry (exponential backoff), otomatis jalankan `deterministic_fallback.py` berbasis selisih $\Delta_j \cdot w_j$ terbesar tanpa menghentikan batch atau memunculkan HTTP 500.
5. **State Machine Batch Seleksi (Bagian 6 PRD):**
   - `Draft` $\rightarrow$ `Collecting` $\rightarrow$ `Calculated` $\rightarrow$ `Narrated` $\rightarrow$ `Approved` $\rightarrow$ `Published`.
   - Portal publik `/cek-bansos` **hanya** boleh menampilkan hasil dari batch yang sudah berstatus `Published`.
6. **Keamanan Portal Publik (FR-06):**
   - Verifikasi menggunakan 16 digit NIK + 4 digit terakhir KK + CAPTCHA.
   - Rate limit 5 req/menit/IP dan *lockout* 15 menit setelah 5 kegagalan verifikasi berturut-turut per NIK.
   - Masking visual selalu aktif di UI (`367403******0002`, `Ahmad S******`). Dekripsi penuh (`nik_encrypted`) hanya diizinkan saat mencetak dokumen PDF Berita Acara resmi kelurahan.

---

## 4. Batasan Proyek (Boundaries)
- **Selalu lakukan:** Jalankan unit test sebelum commit; validasi $\sum w_j = 1.0$; masking PII 100% sebelum memanggil LLM; enkripsi NIK sebelum simpan ke DB; review desain `.stitch` sebelum implementasi UI.
- **Tanya dulu sebelum:** Mengubah skema DB di luar 9 tabel PRD (`CRITERIA`, `SUBCRITERIA`, `BATCH_CRITERIA`, `CITIZEN`, `PERIOD`, `SELECTION_BATCH`, `EVALUATION` [termasuk `real_dependents_count` yang telah disetujui untuk Tie-Breaker Level 3], `EVALUATION_DETAIL`, `SELECTION_RESULT`, `AUDIT_LOG`); menambah dependensi baru di luar stack; menerapkan halaman UI baru dari `.stitch`.
- **Jangan pernah:** Menyimpan NIK plaintext di DB/log; mengirim PII ke Gemini API; memublikasikan hasil sebelum status `Published`; langsung menyalin HTML `.stitch` tanpa perbaikan responsivitas (Desktop, Tablet, Mobile).
