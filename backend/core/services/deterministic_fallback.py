"""
core/services/deterministic_fallback.py — Rule-based Explainable AI Narrative Generator.

PRD References:
  - FR-05: Rule-based fallback text generator invoked when Gemini API is unavailable or fails.
  - Section 8.3: Calculates gap Δ_j = avg_passed_score_j - normalized_score_j for each criterion.
  - Weighted penalty: Δ_j * w_j with canonical tie-breaker C1 -> C2 -> C3 -> C4.
  - Borderline tie-break handler when all Δ_j <= 0.
"""

from __future__ import annotations

from typing import Any

CANONICAL_CRITERIA_ORDER = ["C1", "C2", "C3", "C4"]


def _canonical_sort_key(code: str) -> int:
    try:
        return CANONICAL_CRITERIA_ORDER.index(code)
    except ValueError:
        return 99


def generate_deterministic_fallback(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Generate deterministic, standardized explanations for an applicant.

    For TIDAK_LOLOS:
      - Computes weighted gap Δ_j * w_j = (avg_passed_score - normalized_score) * weight.
      - Selects criterion with maximum Δ_j * w_j, breaking ties using canonical order C1 -> C2 -> C3 -> C4.
      - If all Δ_j <= 0, handles as borderline tie-breaker quota exhaustion.

    For LOLOS:
      - Selects criterion with maximum normalized contribution (normalized_score * weight).
      - Reminds candidate of document verification and distribution schedules.

    Args:
        payload: Anonymous payload dictionary built by build_anonymous_payload().

    Returns:
        dict: {
            "ringkasan_keputusan": str,
            "faktor_penentu_utama": list[str],
            "narasi_lengkap": str,
            "rekomendasi_tindak_lanjut": str,
            "primary_criterion_code": str,
        }
    """
    status = payload.get("status", "TIDAK_LOLOS")
    rank = payload.get("rank") or "-"
    quota = payload.get("quota") or "-"
    final_score = payload.get("final_score", 0.0)
    cutoff_score = payload.get("cutoff_score", 0.0)
    criteria_data = payload.get("criteria_data", [])

    if status == "LOLOS":
        return _generate_lolos_narrative(
            rank=rank,
            quota=quota,
            final_score=final_score,
            cutoff_score=cutoff_score,
            criteria_data=criteria_data,
        )

    # Status: TIDAK_LOLOS
    return _generate_tidak_lolos_narrative(
        rank=rank,
        quota=quota,
        final_score=final_score,
        cutoff_score=cutoff_score,
        criteria_data=criteria_data,
    )


def _generate_tidak_lolos_narrative(
    *,
    rank: Any,
    quota: Any,
    final_score: float,
    cutoff_score: float,
    criteria_data: list[dict[str, Any]],
) -> dict[str, Any]:
    # Compute gaps Δ_j and weighted gaps Δ_j * w_j
    gaps: list[dict[str, Any]] = []
    for item in criteria_data:
        code = item["code"]
        name = item["name"]
        w = float(item["weight"])
        norm = float(item["normalized_score"])
        avg_pass = float(item["avg_passed_score"])
        delta = avg_pass - norm
        weighted_gap = round(delta * w, 6)

        gaps.append({
            "code": code,
            "name": name,
            "weight": w,
            "normalized_score": norm,
            "avg_passed_score": avg_pass,
            "delta": delta,
            "weighted_gap": weighted_gap,
            "canonical_order": _canonical_sort_key(code),
        })

    # Check borderline scenario: candidate has all deltas <= 0
    all_gaps_non_positive = all(g["delta"] <= 0.0001 for g in gaps) if gaps else False

    if all_gaps_non_positive and gaps:
        # Borderline case: candidate lost purely due to tie-breaker or quota exhaustion
        gaps.sort(key=lambda x: x["canonical_order"])
        primary = gaps[0]
        top_factors = [f"{g['name']} ({g['code']})" for g in gaps[:2]]

        summary = (
            f"Berdasarkan kalkulasi SAW, pemohon berada di peringkat {rank} dari kuota {quota} penerima manfaat, "
            "namun belum masuk dalam kuota alokasi karena penentuan batas kuota (cutoff)."
        )

        p1 = (
            f"Berdasarkan hasil kalkulasi Simple Additive Weighting (SAW) Dinas Sosial Kelurahan Jurangmangu Barat, "
            f"Bapak/Ibu Pemohon menempati peringkat {rank} dari kuota {quota} penerima manfaat yang ditetapkan pada periode ini."
        )
        p2 = (
            f"Skor preferensi Bapak/Ibu Pemohon ({final_score:.4f}) berada sangat kompetitif di batas ambang kuota "
            f"(cutoff: {cutoff_score:.4f}). Parameter penilaian menunjukkan kelayakan yang setara dengan rata-rata penerima lolos, "
            "namun alokasi akhir ditentukan melalui mekanisme batas kuota bertingkat (tie-breaker) yang memprioritaskan "
            "kriteria Pendapatan Keluarga (C1) dan Jumlah Tanggungan (C2)."
        )
        p3 = (
            "Apabila terdapat pemutakhiran data kondisi sosial ekonomi keluarga atau tanggungan di masa mendatang, "
            "Bapak/Ibu Pemohon disarankan berkoordinasi dengan pengurus RT setempat untuk periode seleksi selanjutnya."
        )

        full_narrative = f"{p1}\n\n{p2}\n\n{p3}"
        recommendation = "Lakukan pemutakhiran data kondisi keluarga melalui Ketua RT setempat untuk periode seleksi selanjutnya."

        return {
            "ringkasan_keputusan": summary,
            "faktor_penentu_utama": top_factors,
            "narasi_lengkap": full_narrative,
            "rekomendasi_tindak_lanjut": recommendation,
            "primary_criterion_code": primary["code"],
        }

    # Standard TIDAK_LOLOS scenario: rank by largest weighted gap, then canonical order
    # Note: higher weighted_gap means candidate fell shortest behind passed candidates
    gaps.sort(key=lambda x: (-x["weighted_gap"], x["canonical_order"]))

    primary = gaps[0] if gaps else {"code": "C1", "name": "Pendapatan Keluarga", "normalized_score": 0.0, "avg_passed_score": 0.0, "weight": 0.3}
    top_factors = [f"{primary['name']} ({primary['code']})"]

    # Add secondary factor if it also has positive gap
    if len(gaps) > 1 and gaps[1]["delta"] > 0:
        top_factors.append(f"{gaps[1]['name']} ({gaps[1]['code']})")

    summary = (
        f"Berdasarkan kalkulasi SAW, pemohon berada di peringkat {rank} dari kuota {quota} penerima manfaat, "
        f"dengan faktor pembeda utama pada kriteria {primary['name']}."
    )

    p1 = (
        f"Berdasarkan hasil seleksi bantuan sosial Dinas Sosial Kelurahan Jurangmangu Barat menggunakan metode "
        f"Simple Additive Weighting (SAW), Bapak/Ibu Pemohon menempati peringkat {rank} dari kuota {quota} penerima manfaat "
        "yang tersedia pada periode seleksi ini."
    )
    p2 = (
        f"Analisis kesenjangan menunjukkan bahwa faktor pembeda utama ketidaklolosan adalah kriteria {primary['name']} "
        f"({primary['code']}), dengan nilai normalisasi ({primary['normalized_score']:.2f}) yang berada di bawah rata-rata "
        f"penerima yang lolos kuota ({primary['avg_passed_score']:.2f}). Dengan bobot preferensi kelurahan sebesar "
        f"{primary['weight']:.2f}, perbedaan capaian pada kriteria ini memberikan pengaruh terbesar terhadap akumulasi skor preferensi akhir."
    )
    p3 = (
        "Apabila terdapat perubahan kondisi ekonomi keluarga, tanggungan, atau administrasi kependudukan di masa mendatang, "
        "Bapak/Ibu Pemohon dianjurkan melapor ke pengurus RT setempat untuk proses verifikasi dan pemutakhiran data usulan pada periode berikutnya."
    )

    full_narrative = f"{p1}\n\n{p2}\n\n{p3}"
    recommendation = (
        f"Konsultasikan pemutakhiran data kriteria {primary['name']} dan kondisi keluarga ke Ketua RT untuk periode seleksi bansos berikutnya."
    )

    return {
        "ringkasan_keputusan": summary,
        "faktor_penentu_utama": top_factors,
        "narasi_lengkap": full_narrative,
        "rekomendasi_tindak_lanjut": recommendation,
        "primary_criterion_code": primary["code"],
    }


def _generate_lolos_narrative(
    *,
    rank: Any,
    quota: Any,
    final_score: float,
    cutoff_score: float,
    criteria_data: list[dict[str, Any]],
) -> dict[str, Any]:
    # For LOLOS candidates, find the highest positive weighted contributor: normalized_score * weight
    contributions = []
    for item in criteria_data:
        code = item["code"]
        name = item["name"]
        w = float(item["weight"])
        norm = float(item["normalized_score"])
        contrib = round(norm * w, 6)
        contributions.append({
            "code": code,
            "name": name,
            "weight": w,
            "normalized_score": norm,
            "contribution": contrib,
            "canonical_order": _canonical_sort_key(code),
        })

    contributions.sort(key=lambda x: (-x["contribution"], x["canonical_order"]))
    primary = contributions[0] if contributions else {"code": "C1", "name": "Pendapatan Keluarga", "normalized_score": 1.0, "weight": 0.3}

    top_factors = [f"{primary['name']} ({primary['code']})"]
    if len(contributions) > 1 and contributions[1]["contribution"] > 0:
        top_factors.append(f"{contributions[1]['name']} ({contributions[1]['code']})")

    summary = (
        f"Selamat, Bapak/Ibu Pemohon dinyatakan lolos seleksi penerima bantuan sosial di peringkat {rank} "
        f"dari kuota {quota} penerima manfaat."
    )

    p1 = (
        f"Selamat, berdasarkan hasil perhitungan Simple Additive Weighting (SAW) Dinas Sosial Kelurahan Jurangmangu Barat, "
        f"Bapak/Ibu Pemohon dinyatakan lolos seleksi penerima bantuan sosial dengan menempati peringkat {rank} "
        f"dari total kuota {quota} penerima manfaat (skor akhir: {final_score:.4f})."
    )
    p2 = (
        f"Keputusan ini didorong oleh capaian prioritas tinggi pada kriteria {primary['name']} ({primary['code']}) "
        f"dengan skor normalisasi {primary['normalized_score']:.2f} dan bobot preferensi {primary['weight']:.2f}, "
        "yang mencerminkan tingkat pemenuhan syarat bantuan sosial sesuai ketentuan kelurahan."
    )
    p3 = (
        "Mohon menunggu jadwal verifikasi fisik berkas atau informasi jadwal penyaluran resmi bantuan yang akan "
        "diumumkan oleh kantor Kelurahan Jurangmangu Barat atau melalui Ketua RT setempat."
    )

    full_narrative = f"{p1}\n\n{p2}\n\n{p3}"
    recommendation = (
        "Persiapkan dokumen kependudukan (KTP dan Kartu Keluarga asli) untuk verifikasi fisik berkas dan jadwal penyaluran di kantor kelurahan."
    )

    return {
        "ringkasan_keputusan": summary,
        "faktor_penentu_utama": top_factors,
        "narasi_lengkap": full_narrative,
        "rekomendasi_tindak_lanjut": recommendation,
        "primary_criterion_code": primary["code"],
    }
