# Hybrid SAW + Counterfactual XAI: Seleksi Bansos Kelurahan Jurangmangu Barat

## Problem Statement
Bagaimana kita dapat mengubah proses seleksi bantuan sosial di tingkat kelurahan yang selama ini rawan bias subjektif dan minim transparansi menjadi sistem pendukung keputusan hibrida yang 100% objektif secara matematis (SAW) sekaligus memiliki akuntabilitas sosial yang mudah dipahami warga awam (Counterfactual XAI Gemini), tanpa mengorbankan privasi data kependudukan?

## Recommended Direction
Membangun platform **Explainable Decision Support System (EDSS)** berbasis web hibrida yang memadukan komputasi deterministik **Simple Additive Weighting (SAW)** di lapisan backend dengan **Gemini Flash API** sebagai lapisan narasi penjelasan (*Explainer Layer*):
1. **Pemisahan Lingkungan (Decoupled Portals):** Portal publik warga tanpa login yang aman (verifikasi 16 digit NIK + 4 digit terakhir No KK) untuk mengecek status dan narasi, serta dashboard internal terproteksi RBAC untuk aparatur kelurahan (Kasi Kesos, Ketua RT, Lurah).
2. **Zero-Trust Privacy & Symbolic Prompting:** Identitas pribadi warga (Nama, NIK, No KK, Alamat) di-masking 100% sebelum parameter kalkulasi diteruskan ke LLM. Gemini hanya menerima bobot, nilai normalisasi, peringkat, dan nilai ambang batas kuota.
3. **Resilience & Fallback Engine:** Sistem dilengkapi *Deterministic Rule-Based Text Generator* yang otomatis aktif jika layanan API eksternal mengalami kendala atau kehabisan kuota, menjamin keandalan 100% saat pengujian maupun operasional.
4. **Academic-Grade Evaluation:** Modul pengujian metrik akurasi matematis SAW, *fidelity alignment* narasi XAI, dan evaluasi kegunaan *System Usability Scale (SUS)* yang siap dipakai untuk Bab 4 dan Bab 5 Skripsi.

## Key Assumptions to Validate
- [ ] **Akurasi Matematis SAW 100%:** Formula normalisasi dan perankingan di `saw_engine.py` menghasilkan nilai preferensi yang identik dengan hitungan manual Microsoft Excel (target error = 0.0000).
- [ ] **Fidelity & Zero-Hallucination XAI:** Narasi yang dihasilkan Gemini selalu setia terhadap parameter matematis dan kriteria pembeda terbesar tanpa mengarang data palsu (uji validasi skema JSON dan fidelity $\ge 95\%$).
- [ ] **Efektivitas Privasi Portal Publik:** Kombinasi NIK + 4 digit No KK berhasil membatasi akses warga tanpa menambah beban login akun formal.
- [ ] **Penerimaan Pengguna (SUS Score):** Aparatur kelurahan, Ketua RT, dan warga menilai sistem transparan, mudah digunakan, dan mengurangi kecurigaan manipulasi data (target skor SUS $\ge 80$).

## MVP Scope
- **Backend Core:** Django REST Framework dengan service terisolasi `saw_engine.py`, `xai_explainer.py`, dan `deterministic_fallback.py`.
- **Database & Data Management:** PostgreSQL/SQLite dengan skema kriteria dinamis, sub-kriteria crips, data calon KPM, batch seleksi, dan riwayat audit.
- **Data Ingestion:** Form manual per warga dan batch import template Excel dengan validasi format NIK dan baris error.
- **Frontend Presentation:** React.js + Tailwind CSS dengan routing terpisah: portal publik warga (`/cek-bansos`) dengan visualisasi selisih kriteria dan dashboard internal staf (`/dashboard/*`).
- **Pelaporan Resmi:** Generator Berita Acara Penetapan Penerima Bansos (PDF ber-QR Code) dan ekspor rekapitulasi Excel.
- **Evaluasi Skripsi:** Halaman benchmark fidelity XAI dan ekspor dataset uji untuk laporan skripsi.

## Not Doing (and Why)
- **Akun Login Mandiri untuk Warga** — Warga tidak perlu membuat username/password. Friksi registrasi dan lupa sandi akan menghambat adopsi warga lansia/awam. Verifikasi NIK + 4 digit KK jauh lebih praktis dan aman.
- **Fitur Pengajuan Sanggahan Berkas Digital Dua Arah di Web** — Menghindari beban verifikasi berkas digital tak berujung di server kelurahan. Klarifikasi data tetap dilakukan secara kultural melalui Ketua RT saat pemutakhiran data periode berikutnya.
- **Integrasi Langsung Dua Arah ke SIKS-NG Kemensos** — Database SIKS-NG dilindungi regulasi ketat kementerian. Sistem diposisikan sebagai DSS internal kelurahan untuk memvalidasi kelayakan sebelum data final di-input ke SIKS-NG oleh operator resmi.
- **Self-Hosted Local LLM (Ollama/vLLM berat)** — Keterbatasan perangkat keras server di kantor kelurahan. Menggunakan API Gemini Flash dengan *data masking* 100% jauh lebih hemat biaya, cepat (<1.5 detik), dan realistis.

## Open Questions
- Berapa jumlah rata-rata calon KPM yang biasanya diusulkan per periode di Kelurahan Jurangmangu Barat untuk penentuan batas chunking upload Excel?
- Apakah ada kriteria lokal spesifik tambahan di Kelurahan Jurangmangu Barat selain 4 kriteria standar (Pendapatan, Tanggungan, Kondisi Rumah, Aset)?
- Bagaimana format nomor surat dinas resmi kelurahan yang perlu dicantumkan pada template Berita Acara PDF?
