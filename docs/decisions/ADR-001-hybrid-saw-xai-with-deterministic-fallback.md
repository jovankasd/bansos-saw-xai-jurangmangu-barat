# ADR-001: Arsitektur EDSS Hibrida — Komputasi Deterministik SAW dengan Layer XAI Gemini Flash Terkendali dan Fallback Berbasis Aturan

## Status
Accepted

## Date
2026-10-13

## Context
Seleksi Keluarga Penerima Manfaat (KPM) bantuan sosial di Kelurahan Jurangmangu Barat membutuhkan dua sifat yang sering kali saling bertolak belakang:
1. **Kepastian dan Akuntabilitas Matematis:** Peringkat dan status kelolosan harus 100% deterministik, bebas halusinasi, dapat diaudit terhadap perhitungan manual Microsoft Excel ($\text{Error} = 0.0000$), dan adil saat terjadi nilai kembar di batas kuota.
2. **Keterjelasan Bahasa Alami bagi Warga Awam (Transparansi Publik):** Matriks normalisasi $R_{ij}$ dan skor preferensi $V_i$ tidak mudah dipahami oleh warga atau aparat non-teknis. Warga yang tidak lolos membutuhkan penjelasan *counterfactual* yang santun dan spesifik mengenai kriteria mana yang menyebabkan skor mereka berada di bawah ambang kuota (*cutoff*).

Selain itu, ketergantungan pada layanan eksternal (Google Gemini API) memiliki risiko *rate-limit* (HTTP 429), gangguan jaringan, atau respons JSON yang tidak sesuai skema.

## Decision
Kami memisahkan secara tegas **Decision Layer** dan **Explainer Layer**:
1. **Decision Layer (100% Deterministik):** Perhitungan normalisasi matriks $R_{ij}$, skor akhir $V_i = \sum w_j r_{ij}$, dan *hierarchical tie-breaking* dilakukan sepenuhnya oleh modul Python (`saw_engine.py` dan `tie_breaker.py`) menggunakan tipe data `Decimal` presisi tetap. LLM **dilarang** menentukan atau mengubah skor maupun peringkat.
2. **Explainer Layer (Constrained XAI Gemini Flash):** Google Gemini Flash (`temperature: 0.15`, `response_mime_type: "application/json"`) hanya menerima *payload* numerik hasil akhir SAW beserta rata-rata skor kandidat lolos ($\bar{r}_j^{\text{lolos}}$) untuk menyusun narasi penjelasan *counterfactual*.
3. **Rule-Based Deterministic Fallback (`deterministic_fallback.py`):** Jika Gemini API gagal setelah 2 kali *retry* (*exponential backoff*) atau menghasilkan output yang melanggar validasi kesetiaan (*fidelity/hallucination check*), sistem otomatis membangkitkan narasi standar berbasis rumus kesenjangan terbobot terbesar:
   $$\operatorname{argmax}_{j} \left( (\bar{r}_j^{\text{lolos}} - r_{ij}) \cdot w_j \right)$$

## Alternatives Considered

### Alternatif 1: End-to-End LLM Decision Making (LLM memilih dan meranking KPM secara langsung)
- **Pros:** Implementasi singkat, langsung menghasilkan ranking dan alasan sekaligus.
- **Cons:** Non-deterministik, rentan bias dan halusinasi angka, tidak dapat diaudit secara matematis oleh Inspektorat/BPKP.
- **Rejected:** Melanggar syarat utama akuntabilitas layanan publik dan target akurasi 100% terhadap perhitungan manual.

### Alternatif 2: Self-Hosted Local LLM (Llama-3 / Mistral di Server Kelurahan)
- **Pros:** Data tidak keluar dari jaringan lokal.
- **Cons:** Infrastruktur server kelurahan tidak memiliki GPU; inferensi CPU untuk 100–300 KPM membutuhkan waktu berjam-jam.
- **Rejected:** Tidak realistis secara infrastruktur (lihat PRD Bagian 12 Poin 4). Risiko privasi cloud diatasi melalui *Zero-PII Sanitization* (ADR-002).

### Alternatif 3: Hanya Template Statis Tanpa LLM
- **Pros:** Cepat dan bebas biaya API.
- **Cons:** Penjelasan menjadi kaku/robotik ketika mengombinasikan beberapa faktor *counterfactual* sekaligus.
- **Rejected:** Kurang komunikatif bagi warga, namun tetap dipertahankan sebagai *Fallback Engine* (`deterministic_fallback.py`) untuk menjamin *zero downtime*.

## Consequences
- Perhitungan ranking SAW dapat diselesaikan secara instan (< 2 detik untuk 100–300 KPM) dan terpisah dari proses pembangkitan narasi XAI.
- Sistem tidak pernah menghasilkan *HTTP 500 Internal Server Error* ketika kuota Gemini API habis karena `deterministic_fallback.py` mengambil alih secara transparan dan menandai `explanation_source = "DETERMINISTIC_FALLBACK"`.
- Kualitas penjelasan AI dapat diukur secara matematis menggunakan metrik **Fidelity Score** ($\ge 95.0\%$) dan **Hallucination Rate** ($0.0\%$) pada Bab 4 Skripsi.
