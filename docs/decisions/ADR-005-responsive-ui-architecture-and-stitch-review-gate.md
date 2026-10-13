# ADR-005: Arsitektur UI Responsif 3-Tier (Mobile, Tablet, Desktop) dan Gerbang Review Desain `.stitch`

## Status
Accepted

## Date
2026-10-13

## Context
Folder `.stitch/designs/` menyediakan 6 prototipe visual bertema **Civic Precision** (`#003426` Emerald Civic, font `Hanken Grotesk` dan `JetBrains Mono`). Namun hasil audit awal menemukan sejumlah masalah struktural pada file HTML mentah di `.stitch/designs/`:
1. **Tidak Responsif untuk Tablet dan Handphone (Mobile):** Kelima layar dashboard menggunakan `<aside class="fixed top-0 left-0 h-screen w-64">` dan `pl-64`/`pl-72` secara permanen tanpa *breakpoint* responsif, sehingga tampilan hancur di layar `< 1024px`.
2. **Elemen Terpotong (Clipped) dan Bertumpuk:** Tombol aksi dan kartu profil di sebelah kanan Topbar terpotong keluar layar; tabel SAW 11 kolom terjepit di dalam grid 8 kolom; kartu metrik nominal rupiah di halaman XAI terpotong.
3. **Deviasi terhadap PRD v3.0:** Kriteria $C_4$ tidak konsisten (tertulis *"Daya Listrik 900 VA"* di sebagian halaman, padahal PRD menetapkan **"Kepemilikan Aset"**), menu sidebar berbeda-beda antar-file, dan terdapat fitur yang dilarang di PRD Bagian 12 (*form sanggahan dua arah di portal publik* serta *tombol Sinkronisasi DTKS*).

## Decision
Kami menetapkan aturan arsitektur *frontend* sebagai berikut:
1. **Larangan Copy-Paste Mentah & Gerbang Review Wajib (Mandatory Design Review Gate):**
   File `.stitch/designs/*.html` hanya digunakan sebagai referensi *design tokens* dan komposisi visual. Sebelum mengimplementasikan setiap halaman React, pengembang/agen wajib mempresentasikan rincian perapihan tata letak kepada pengguna untuk disetujui.
2. **Arsitektur Layout Responsif 3-Tier (Mobile-First Tailwind CSS):**
   - **Mobile / Handphone (`< 768px` / `base`, `sm`):** Sidebar menjadi *Off-Canvas Slide-Over Drawer* dengan backdrop gelap dan tombol *Hamburger* di Topbar (`lg:hidden`). Grid kartu disusun 1 kolom (`grid-cols-1`), tabel matriks memiliki *wrapper* `overflow-x-auto` dengan kolom nama *sticky* atau opsi kartu ringkas, dan tinggi area sentuh minimal `40px–44px`.
   - **Tablet (`768px – 1023px` / `md`):** Sidebar tetap berupa *drawer* yang dapat dibuka-tutup, kartu metrik disusun 2 kolom (`md:grid-cols-2`), dan layout *master-detail* (tabel SAW + detail matriks, antrean XAI + detail narasi) ditumpuk vertikal agar tidak ada teks yang terjepit.
   - **Desktop / Browser (`>= 1024px` / `lg`, `xl`):** Sidebar tetap di kiri (`lg:fixed lg:w-64`), kontainer utama `lg:pl-64`, Topbar menggunakan `flex-wrap` yang rapi tanpa elemen terpotong, dan panel *master-detail* berdampingan pada `xl:grid-cols-12`.
3. **Penyelarasan Penuh dengan PRD v3.0:**
   - Menyeragamkan $C_1$ (Pendapatan, Cost 30%), $C_2$ (Tanggungan, Benefit 25%), $C_3$ (Kondisi Rumah, Benefit 25%), dan $C_4$ (Kepemilikan Aset, Cost 20%) di seluruh layar.
   - Menyatukan navigasi Sidebar dengan pemfilteran hak akses (RBAC) untuk `SUPER_ADMIN` (Kasi Kesos), `SURVEYOR` (Ketua RT), dan `VIEWER` (Lurah).
   - Menghapus form sanggahan dua arah di portal publik dan tombol sinkronisasi DTKS.

## Alternatives Considered

### Alternatif 1: Konversi Langsung HTML `.stitch` ke Komponen JSX (1:1 Static Port)
- **Pros:** Sangat cepat diselesaikan.
- **Cons:** Mewarisi seluruh bug tampilan terpotong, tidak bisa dibuka di HP/Tablet (merusak skor pengujian SUS warga dan Ketua RT), serta melanggar PRD Bagian 12.
- **Rejected:** Kualitas tampilan dan fleksibilitas *multi-device* (Desktop, Tablet, Mobile) adalah syarat eksplisit pengguna dan penentu keberhasilan uji penerimaan pengguna (SUS $\ge 80.0$).

## Consequences
- Seluruh halaman dapat diakses dengan nyaman baik oleh warga menggunakan Handphone di `/cek-bansos`, Ketua RT menggunakan Tablet/HP di lapangan, maupun Kasi Kesos dan Lurah menggunakan Desktop di kantor kelurahan.
- Terdapat 1 komponen `<AppShell />` terpusat yang menjaga konsistensi Sidebar, Topbar, dan RBAC di seluruh halaman dashboard.
