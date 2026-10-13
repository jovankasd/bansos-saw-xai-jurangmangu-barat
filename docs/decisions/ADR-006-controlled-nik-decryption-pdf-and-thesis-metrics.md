# ADR-006: Dekripsi Terkontrol NIK pada Berita Acara PDF Resmi, Penjagaan Zero-PII Publik, dan Metrik Evaluasi Skripsi

## Status
Accepted

## Date
2026-10-13

## Context
Sistem Pendukung Keputusan (SPK) Seleksi Bantuan Sosial Kelurahan Jurangmangu Barat harus memenuhi dua tuntutan hukum dan akademis sekaligus:
1. **Kepatuhan Hukum Administrasi Pemerintahan & UU PDP No. 27/2022:**
   - Surat Berita Acara Penetapan Penerima Bansos adalah dokumen legal fisik yang ditandatangani oleh Lurah dan Kasi Kesos, sehingga wajib memuat NIK asli (16 digit) calon penerima bantuan yang lolos serta lampiran warga Tidak Memenuhi Syarat (TMS).
   - Di sisi lain, UU PDP No. 27/2022 melarang keras penyimpanan atau pengeksposan NIK plaintext secara terbuka di database, log audit, atau portal publik warga.
2. **Kebutuhan Evaluasi Akademis Skripsi (Bab 4 & Bab 5):**
   - Diperlukan instrumen kuantitatif otomatis untuk mengukur kesetiaan narasi XAI (*Fidelity Score*) terhadap kesenjangan terbobot SAW ($\Delta_{i,j} \cdot w_j$) menggunakan snapshot bobot beku `BatchCriteria.frozen_weight`.
   - Diperlukan instrumen pendeteksi halusinasi numerik dan kriteria fiktif (*Hallucination Rate*) yang dapat mengenali gaya penulisan desimal koma Bahasa Indonesia (`0,684`) dan persentase (`60%`).
   - Diperlukan kuesioner baku System Usability Scale (SUS 10-item) dan ekspor dataset pengujian ke format lembar kerja Excel (`.xlsx`).

## Decision
Kami menetapkan keputusan arsitektural pelaporan dokumen dan evaluasi akademis sebagai berikut:

1. **Dekripsi NIK Terkontrol Ketat Eksklusif Berita Acara PDF:**
   - Dekripsi kolom `nik_encrypted` menggunakan `AES-256-GCM` diizinkan **hanya dan hanya pada** fungsi `generate_berita_acara_pdf()`.
   - Setiap kali Berita Acara dicetak, sistem secara atomik mencatat peristiwa tersebut ke `AuditLog` dengan aksi `action=AuditLog.Action.NIK_DECRYPT`.
   - Detail log audit dilarang keras menyimpan NIK plaintext 16 digit guna mencegah kebocoran data sekunder pada log sistem.
   - Berita Acara PDF dilengkapi kop surat resmi Kelurahan Jurangmangu Barat, tabel ranking KPM lolos, lampiran terpisah warga TMS (`DISQUALIFIED`), tanda tangan formal Kasi Kesos & Lurah, serta QR Code verifikasi dokumen.

2. **Perlindungan Zero-PII Dokumen Publik Warga (`/result-pdf`):**
   - Dokumen transparansi individual untuk warga via portal publik wajib menggunakan penyamaran visual 100% (`nik_masked` dan `full_name_masked`).
   - Akses publik diamankan menggunakan token bertanda tangan kriptografis (`sign_pdf_download_token`/`verify_pdf_download_token`) dengan *Time-To-Live* 15 menit, dan hanya dapat diunduh jika batch telah berstatus resmi `Published`.

3. **Formula Evaluasi Akademis Skripsi (Fidelity & Hallucination):**
   - **Fidelity Score:** Dihitung sesuai rumus PRD Bagian 11.2:
     $$\text{Fidelity Score} = \frac{1}{|K_{\text{TL}}|} \sum_{i \in K_{\text{TL}}} \mathbb{I}\left( C_{\text{AI\_primary}}(i) == \operatorname{argmax}_j (\Delta_{i,j} \cdot w_j) \right)$$
     Jika $|K_{\text{TL}}| == 0$ (seluruh kandidat lolos alokasi kuota), fungsi mengembalikan nilai `100.0%` secara aman tanpa menimbulkan `ZeroDivisionError`.
   - **Hallucination Rate:** Mendeteksi kemunculan kriteria asing di luar $\{C_1, \dots, C_n\}$ atau istilah terlarang (`daya listrik`), serta angka desimal fiktif yang tidak ada pada payload input setelah dinormalisasi terhadap koma desimal Indonesia (`0,684` $\rightarrow$ `0.684`) dan persentase (`60%` $\rightarrow$ `0.60`).
   - **SUS & Ekspor Dataset:** Menyediakan template kuesioner 10 butir SUS (Brooke, 1996) berbahasa Indonesia dan fungsi ekspor data uji multi-sheet ke berkas Excel (`.xlsx`).

## Alternatives Considered

### Alternatif 1: Menampilkan NIK Masked pada Berita Acara PDF Resmi
- **Pros:** Lebih aman dari sisi data leakage jika berkas PDF hilang.
- **Cons:** Dokumen Berita Acara menjadi cacat secara hukum administrasi pemerintahan daerah, karena dinas sosial dan bank penyalur bansos mewajibkan NIK lengkap 16 digit yang sah untuk pencairan dana/sembako.
- **Rejected:** Diperlukan dekripsi terkontrol dengan audit trail penuh (`NIK_DECRYPT`).

### Alternatif 2: Menggunakan Layanan Pihak Ketiga (Headless Chrome / WeasyPrint)
- **Pros:** Desain CSS berbasis HTML.
- **Cons:** Memerlukan runtime biner tambahan eksternal yang berat, overhead memori tinggi, dan rentan terhadap kegagalan dependensi sistem operasi (cairo/pango).
- **Rejected:** ReportLab v5.0.1 murni Python, sangat cepat (waktu render < 100 ms), hemat memori (`io.BytesIO`), dan sudah terinstal dengan baik di lingkungan server.

## Consequences
- Kasi Kesos dan Lurah dapat langsung mengunduh dan mencetak Berita Acara fisik resmi berstandar kelurahan lengkap dengan QR Code validasi keaslian.
- Hak privasi warga pada portal publik tetap terjaga 100% tanpa adanya risiko pencurian data identitas.
- Seluruh pengujian Bab 4 dan Bab 5 skripsi (akurasi SAW, kesetiaan narasi XAI, bebas halusinasi, dan penerimaan SUS) didukung oleh endpoint dan instrumen komputasi otomatis yang siap digunakan.
