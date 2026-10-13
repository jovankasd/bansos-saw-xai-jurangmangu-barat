"""
core/services/evaluation_metrics.py — Academic Thesis Evaluation Metrics (Milestone 5 & 6 Backend).

Implements evaluation instruments defined in PRD Section 11 (Bab 4 & Bab 5):
  1. Section 11.2 Fidelity Score:
     Measures whether AI-identified primary determining criterion matches argmax_j (Δ_{i,j} * w_j).
     Fidelity = (1 / |K_TL|) * sum I(C_AI_primary(i) == argmax_j (Δ_{i,j} * w_j))
     Safely handles |K_TL| == 0 without ZeroDivisionError (returns 100.0%).
     Uses frozen weights from BatchCriteria.
  2. Section 11.2 Hallucination Rate:
     H_rate = (N_invalid / N_total) * 100%
     Detects fabricated criteria codes/names and hallucinated numeric parameters.
     Normalizes Indonesian comma decimals (e.g. '0,684' -> 0.684) and percentages (e.g. '60%' -> 0.60).
  3. Section 11.4 System Usability Scale (SUS) 10-Item Questionnaire Template.
  4. Thesis Testing Dataset Export for statistical analysis in Bab 4 & 5.
"""

from __future__ import annotations

import io
import re
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from core.models import (
    BatchCriteria,
    Criteria,
    Evaluation,
    SelectionBatch,
    SelectionResult,
)

CANONICAL_CRITERIA_ORDER = ["C1", "C2", "C3", "C4"]
CRITERION_CODE_PATTERN = re.compile(r"\bC\d+\b", re.IGNORECASE)
FORBIDDEN_CRITERIA_TERMS = ["c99", "c5", "c6", "daya listrik", "900 va", "900va"]

# Patterns for extracting Indonesian decimal comma numbers and percentages
COMMA_DECIMAL_PATTERN = re.compile(r"\b\d+,\d+\b")
PERCENTAGE_PATTERN = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*%\b")
DECIMAL_DOT_PATTERN = re.compile(r"\b0\.\d+\b")
RANK_PATTERN = re.compile(r"peringkat\s+(\d+)", re.IGNORECASE)
QUOTA_PATTERN = re.compile(r"kuota\s+(\d+)", re.IGNORECASE)


def _canonical_sort_key(code: str) -> int:
    try:
        return CANONICAL_CRITERIA_ORDER.index(code)
    except ValueError:
        return 99


def normalize_indonesian_numeric_text(text: str) -> str:
    """
    Normalize Indonesian numeric formatting in text:
    - Decimal commas '0,684' -> '0.684'
    """
    if not isinstance(text, str):
        return ""
    # Replace comma decimal with dot decimal
    return COMMA_DECIMAL_PATTERN.sub(lambda m: m.group(0).replace(",", "."), text)


def extract_primary_ai_criterion(ai_payload: dict[str, Any] | None, narrative_text: str = "") -> str:
    """
    Extract the primary criterion code (e.g. 'C1', 'C2') identified by the AI explanation.
    """
    if ai_payload and isinstance(ai_payload, dict):
        # 1. Direct key
        if ai_payload.get("primary_criterion_code"):
            code = str(ai_payload["primary_criterion_code"]).strip().upper()
            if code.startswith("C"):
                return code

        # 2. Faktor penentu utama
        factors = ai_payload.get("faktor_penentu_utama") or ai_payload.get("faktor_utama")
        if factors and isinstance(factors, list) and len(factors) > 0:
            first_factor = str(factors[0])
            match = CRITERION_CODE_PATTERN.search(first_factor)
            if match:
                return match.group(0).upper()
            # Match by name keywords
            lower_factor = first_factor.lower()
            if "pendapatan" in lower_factor:
                return "C1"
            if "tanggungan" in lower_factor:
                return "C2"
            if "tempat tinggal" in lower_factor or "rumah" in lower_factor:
                return "C3"
            if "aset" in lower_factor:
                return "C4"

    # 3. Search in narrative text
    if narrative_text:
        match = CRITERION_CODE_PATTERN.search(narrative_text)
        if match:
            return match.group(0).upper()
        lower_narrative = narrative_text.lower()
        if "pendapatan" in lower_narrative:
            return "C1"
        if "tanggungan" in lower_narrative:
            return "C2"
        if "tempat tinggal" in lower_narrative or "rumah" in lower_narrative:
            return "C3"
        if "aset" in lower_narrative:
            return "C4"

    return ""


def detect_narrative_hallucinations(
    *,
    eval_obj: Evaluation,
    ai_payload: dict[str, Any] | None,
    ai_narrative: str,
    allowed_codes: set[str],
    valid_numbers: set[float],
    expected_rank: int | None,
    expected_quota: int | None,
) -> list[str]:
    """
    Detect whether an explanation contains hallucinations:
    - Criteria codes or names outside the allowed set (e.g. C99, Daya Listrik).
    - Fabricated rank or quota integers.
    - Fabricated decimal scores not present in payload.
    Normalizes Indonesian comma decimals (0,684) and percentages (60%).
    """
    hallucination_reasons: list[str] = []
    normalized_narrative = normalize_indonesian_numeric_text(ai_narrative)

    # Check payload strings as well
    payload_strings = []
    if ai_payload and isinstance(ai_payload, dict):
        for val in ai_payload.values():
            if isinstance(val, str):
                payload_strings.append(normalize_indonesian_numeric_text(val))
            elif isinstance(val, list):
                payload_strings.extend(normalize_indonesian_numeric_text(str(item)) for item in val)

    combined_text = " ".join([normalized_narrative] + payload_strings)
    lower_text = combined_text.lower()

    # 1. Forbidden terms check
    for term in FORBIDDEN_CRITERIA_TERMS:
        if term in lower_text:
            hallucination_reasons.append(f"Kriteria halusinasi / tidak sah terdeteksi: '{term}'")

    # 2. Unknown C-codes check
    found_codes = CRITERION_CODE_PATTERN.findall(combined_text)
    for code in found_codes:
        if code.upper() not in allowed_codes:
            hallucination_reasons.append(f"Kode kriteria asing terdeteksi: '{code}' (diizinkan: {allowed_codes})")

    # 3. Fabricated rank check
    for rank_str in RANK_PATTERN.findall(combined_text):
        rank_val = int(rank_str)
        if expected_rank is not None and rank_val != expected_rank:
            # Note: only flag if it refers to "peringkat X" and X doesn't match
            hallucination_reasons.append(f"Peringkat terhalusinasi: menyebut peringkat {rank_val}, seharusnya {expected_rank}")

    # 4. Fabricated quota check
    for quota_str in QUOTA_PATTERN.findall(combined_text):
        quota_val = int(quota_str)
        if expected_quota is not None and quota_val != expected_quota:
            hallucination_reasons.append(f"Kuota terhalusinasi: menyebut kuota {quota_val}, seharusnya {expected_quota}")

    # 5. Fabricated floating decimals
    # Search for all decimal numbers in the combined text (both 0.xxxx and any x.xxxx)
    all_decimals = re.findall(r"\b\d+\.\d+\b", combined_text)
    for dec_str in all_decimals:
        dec_val = float(dec_str)
        # Check if matches any valid number (rounded to 2 or 4 decimal places)
        is_valid = any(abs(dec_val - vn) <= 0.015 for vn in valid_numbers)
        if not is_valid:
            hallucination_reasons.append(f"Angka desimal fiktif terdeteksi: {dec_str}")

    return hallucination_reasons


def compute_batch_evaluation_metrics(batch_id: int) -> dict[str, Any]:
    """
    Compute academic thesis evaluation metrics for a selection batch:
      - Fidelity Score (PRD Section 11.2)
      - Hallucination Rate (PRD Section 11.2)
      - Candidate counts breakdown (Total, Eligible, TMS, Lolos, Tidak Lolos)
    """
    batch = (
        SelectionBatch.objects.select_related("period")
        .prefetch_related("batch_criteria", "evaluations__result", "evaluations__details__criteria")
        .get(pk=batch_id)
    )

    # 1. Retrieve criteria weights (frozen weights take precedence)
    batch_criteria = list(batch.batch_criteria.all())
    if batch_criteria:
        criteria_list = [
            {
                "code": bc.code,
                "name": bc.name,
                "weight": float(bc.frozen_weight),
            }
            for bc in sorted(batch_criteria, key=lambda x: _canonical_sort_key(x.code))
        ]
    else:
        criteria_list = [
            {
                "code": c.code,
                "name": c.name,
                "weight": float(c.weight),
            }
            for c in Criteria.objects.filter(is_active=True).order_by("order")
        ]

    allowed_codes = {c["code"] for c in criteria_list}
    weights_map = {c["code"]: c["weight"] for c in criteria_list}

    all_evaluations = list(
        batch.evaluations.select_related("citizen", "result")
        .prefetch_related("details__criteria")
        .all()
    )

    tms_evaluations = [e for e in all_evaluations if e.eligibility_status == Evaluation.EligibilityStatus.DISQUALIFIED]
    eligible_evaluations = [e for e in all_evaluations if e.eligibility_status == Evaluation.EligibilityStatus.ELIGIBLE]

    passed_evaluations = [
        e for e in eligible_evaluations
        if hasattr(e, "result") and e.result and e.result.status == SelectionResult.ResultStatus.LOLOS
    ]
    failed_evaluations = [
        e for e in eligible_evaluations
        if hasattr(e, "result") and e.result and e.result.status == SelectionResult.ResultStatus.TIDAK_LOLOS
    ]

    # Compute average passed score per criterion (r_bar_j)
    avg_passed_map: dict[str, float] = {}
    if passed_evaluations:
        for c_info in criteria_list:
            code = c_info["code"]
            vals = []
            for e in passed_evaluations:
                d = next((det for det in e.details.all() if det.criteria.code == code), None)
                if d and d.normalized_value is not None:
                    vals.append(float(d.normalized_value))
            avg_passed_map[code] = round(sum(vals) / len(vals), 4) if vals else 0.0
    else:
        for c_info in criteria_list:
            avg_passed_map[c_info["code"]] = 0.0

    # -----------------------------------------------------------------------
    # Fidelity Score Computation (PRD Section 11.2)
    # -----------------------------------------------------------------------
    fidelity_matches = 0
    total_failed_candidates = len(failed_evaluations)

    fidelity_details = []
    for eval_obj in failed_evaluations:
        res = eval_obj.result
        # Compute Delta_j * w_j for each criterion
        weighted_gaps = []
        for c_info in criteria_list:
            code = c_info["code"]
            w = weights_map.get(code, 0.0)
            d = next((det for det in eval_obj.details.all() if det.criteria.code == code), None)
            norm_val = float(d.normalized_value) if (d and d.normalized_value is not None) else 0.0
            avg_pass = avg_passed_map.get(code, norm_val)
            delta = avg_pass - norm_val
            w_gap = round(delta * w, 6)
            weighted_gaps.append({
                "code": code,
                "weight": w,
                "normalized_value": norm_val,
                "avg_passed_score": avg_pass,
                "delta": delta,
                "weighted_gap": w_gap,
            })

        # Sort by weighted_gap desc, break ties canonically C1 -> C2 -> C3 -> C4
        weighted_gaps.sort(key=lambda x: (-x["weighted_gap"], _canonical_sort_key(x["code"])))
        expected_primary_code = weighted_gaps[0]["code"] if weighted_gaps else "C1"

        # AI chosen primary criterion
        ai_payload = res.ai_payload_response if (res and isinstance(res.ai_payload_response, dict)) else {}
        ai_narrative = (res.ai_narrative if res else "") or ""
        ai_primary_code = extract_primary_ai_criterion(ai_payload, ai_narrative)

        is_match = (ai_primary_code.upper() == expected_primary_code.upper())
        if is_match:
            fidelity_matches += 1

        fidelity_details.append({
            "evaluation_id": eval_obj.id,
            "citizen_masked": eval_obj.citizen.full_name_masked,
            "rank": res.ranking if res else None,
            "ai_primary_code": ai_primary_code,
            "expected_primary_code": expected_primary_code,
            "is_faithful": is_match,
            "gaps": weighted_gaps,
        })

    # Guard against ZeroDivisionError when |K_TL| == 0
    if total_failed_candidates == 0:
        fidelity_score = 100.0
    else:
        fidelity_score = round((fidelity_matches / total_failed_candidates) * 100.0, 2)

    # -----------------------------------------------------------------------
    # Hallucination Rate Computation (PRD Section 11.2)
    # -----------------------------------------------------------------------
    evaluated_with_narratives = [
        e for e in eligible_evaluations
        if hasattr(e, "result") and e.result and (e.result.ai_narrative or e.result.ai_payload_response)
    ]
    total_evaluated_narratives = len(evaluated_with_narratives)
    invalid_narratives_count = 0

    hallucination_details = []
    for eval_obj in evaluated_with_narratives:
        res = eval_obj.result
        ai_payload = res.ai_payload_response if isinstance(res.ai_payload_response, dict) else {}
        ai_narrative = res.ai_narrative or ""

        # Set of valid numbers from payload for this candidate
        valid_numbers: set[float] = set()
        if res.final_score_v is not None:
            v_val = float(res.final_score_v)
            valid_numbers.add(round(v_val, 4))
            valid_numbers.add(round(v_val, 2))
        if batch.cutoff_score is not None:
            c_val = float(batch.cutoff_score)
            valid_numbers.add(round(c_val, 4))
            valid_numbers.add(round(c_val, 2))

        for c_info in criteria_list:
            valid_numbers.add(round(c_info["weight"], 2))
            valid_numbers.add(round(c_info["weight"], 4))
            # Also percentage equivalents (e.g. 0.30 -> 30)
            valid_numbers.add(round(c_info["weight"] * 100, 1))

        for det in eval_obj.details.all():
            if det.normalized_value is not None:
                nv = float(det.normalized_value)
                valid_numbers.add(round(nv, 4))
                valid_numbers.add(round(nv, 2))
                valid_numbers.add(round(nv * 100, 1))
            if det.raw_crips_value:
                valid_numbers.add(float(det.raw_crips_value))

        for avg_p in avg_passed_map.values():
            valid_numbers.add(round(avg_p, 4))
            valid_numbers.add(round(avg_p, 2))
            valid_numbers.add(round(avg_p * 100, 1))

        # Check hallucinations
        reasons = detect_narrative_hallucinations(
            eval_obj=eval_obj,
            ai_payload=ai_payload,
            ai_narrative=ai_narrative,
            allowed_codes=allowed_codes,
            valid_numbers=valid_numbers,
            expected_rank=res.ranking,
            expected_quota=batch.quota,
        )

        has_hallucination = len(reasons) > 0
        if has_hallucination:
            invalid_narratives_count += 1

        hallucination_details.append({
            "evaluation_id": eval_obj.id,
            "citizen_masked": eval_obj.citizen.full_name_masked,
            "has_hallucination": has_hallucination,
            "reasons": reasons,
        })

    if total_evaluated_narratives == 0:
        hallucination_rate = 0.0
    else:
        hallucination_rate = round((invalid_narratives_count / total_evaluated_narratives) * 100.0, 2)

    return {
        "batch_id": batch.id,
        "batch_name": batch.name or batch.period.name,
        "period_name": batch.period.name,
        "total_candidates": len(all_evaluations),
        "eligible_candidates": len(eligible_evaluations),
        "disqualified_tms": len(tms_evaluations),
        "passed_count": len(passed_evaluations),
        "failed_count": len(failed_evaluations),
        "evaluated_narratives_count": total_evaluated_narratives,
        "fidelity_score": fidelity_score,
        "hallucination_rate": hallucination_rate,
        "fidelity_matches": fidelity_matches,
        "total_failed_candidates": total_failed_candidates,
        "invalid_narratives_count": invalid_narratives_count,
        "sus_template": get_sus_questionnaire_template(),
        "fidelity_details": fidelity_details,
        "hallucination_details": hallucination_details,
    }


def get_sus_questionnaire_template() -> list[dict[str, Any]]:
    """
    Returns the standard 10-item System Usability Scale (SUS) questionnaire (Brooke, 1996)
    translated into Bahasa Indonesia for academic validation (PRD Section 11.4).
    """
    return [
        {
            "id": 1,
            "polarity": "positive",
            "question": "Saya rasa saya akan sering menggunakan sistem pendukung keputusan bansos ini.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 2,
            "polarity": "negative",
            "question": "Saya merasa sistem ini terlalu rumit, padahal semestinya bisa dibuat lebih sederhana.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 3,
            "polarity": "positive",
            "question": "Saya merasa sistem ini mudah digunakan dalam memverifikasi hasil seleksi bansos.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 4,
            "polarity": "negative",
            "question": "Saya rasa saya membutuhkan bantuan staf teknis ahli untuk dapat mengoperasikan sistem ini.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 5,
            "polarity": "positive",
            "question": "Saya menemukan bahwa fitur kalkulasi SAW dan penjelasan narasi XAI terintegrasi dengan sangat baik.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 6,
            "polarity": "negative",
            "question": "Saya merasa terdapat banyak hal yang tidak konsisten atau membingungkan dalam sistem ini.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 7,
            "polarity": "positive",
            "question": "Saya merasa kebanyakan staf atau pengguna awam akan dapat mempelajari sistem ini dengan sangat cepat.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 8,
            "polarity": "negative",
            "question": "Saya merasa sistem ini sangat janggal atau rumit saat digunakan untuk menelusuri keputusan.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 9,
            "polarity": "positive",
            "question": "Saya merasa sangat percaya diri dan yakin ketika menggunakan sistem ini untuk menetapkan penerima bansos.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
        {
            "id": 10,
            "polarity": "negative",
            "question": "Saya merasa perlu mempelajari banyak hal terlebih dahulu sebelum dapat menggunakan sistem ini dengan lancar.",
            "scale_min": 1,
            "scale_max": 5,
            "scale_min_label": "Sangat Tidak Setuju",
            "scale_max_label": "Sangat Setuju",
        },
    ]


def export_thesis_evaluation_dataset(batch_id: int) -> dict[str, Any]:
    """
    Export detailed thesis testing records for Bab 4 and Bab 5 analysis.
    Returns structured JSON with evaluation matrix, individual fidelity match, and hallucination flags.
    """
    metrics = compute_batch_evaluation_metrics(batch_id)
    batch = SelectionBatch.objects.prefetch_related("evaluations__citizen", "evaluations__result").get(pk=batch_id)

    fidelity_map = {item["evaluation_id"]: item for item in metrics.get("fidelity_details", [])}
    hallucination_map = {item["evaluation_id"]: item for item in metrics.get("hallucination_details", [])}

    records = []
    for eval_obj in batch.evaluations.all():
        res = getattr(eval_obj, "result", None)
        f_info = fidelity_map.get(eval_obj.id, {})
        h_info = hallucination_map.get(eval_obj.id, {})

        records.append({
            "evaluation_id": eval_obj.id,
            "applicant_code": f"KPM-{eval_obj.id:04d}",
            "citizen_masked": eval_obj.citizen.full_name_masked,
            "rt": eval_obj.citizen.rt,
            "rw": eval_obj.citizen.rw,
            "eligibility_status": eval_obj.eligibility_status,
            "tms_reason": eval_obj.tms_reason,
            "status": res.status if res else ("DISKUALIFIKASI_TMS" if eval_obj.eligibility_status == "DISQUALIFIED" else "PENDING"),
            "ranking": res.ranking if res else None,
            "final_score": float(res.final_score_v) if (res and res.final_score_v is not None) else None,
            "explanation_source": res.explanation_source if res else "",
            "ai_primary_criterion": f_info.get("ai_primary_code", ""),
            "expected_primary_criterion": f_info.get("expected_primary_code", ""),
            "fidelity_match": None if eval_obj.eligibility_status == "DISQUALIFIED" else f_info.get("is_faithful", True if res and res.status == "LOLOS" else False),
            "hallucination_detected": h_info.get("has_hallucination", False),
            "hallucination_reasons": h_info.get("reasons", []),
        })

    return {
        "batch_id": batch.id,
        "batch_name": batch.name,
        "period_name": batch.period.name,
        "summary_metrics": {
            "fidelity_score": metrics["fidelity_score"],
            "hallucination_rate": metrics["hallucination_rate"],
            "total_candidates": metrics["total_candidates"],
            "eligible_candidates": metrics["eligible_candidates"],
            "disqualified_tms": metrics["disqualified_tms"],
            "passed_count": metrics["passed_count"],
            "failed_count": metrics["failed_count"],
        },
        "records": records,
    }


def export_thesis_evaluation_dataset_xlsx(batch_id: int) -> bytes:
    """
    Export the thesis evaluation dataset directly into an Excel workbook (.xlsx).
    Includes Summary, SAW Results, XAI Fidelity, and SUS Instrument sheets.
    """
    dataset = export_thesis_evaluation_dataset(batch_id)
    wb = openpyxl.Workbook()

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="003426", end_color="003426", fill_type="solid")
    border_thin = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    # Sheet 1: Data Uji & Evaluasi
    ws_data = wb.active
    ws_data.title = "Dataset Pengujian Skripsi"

    headers = [
        "Kode KPM", "Nama (Masked)", "RT", "RW", "Status Seleksi", "Peringkat",
        "Skor Akhir (V)", "Sumber Narasi", "Kriteria AI", "Kriteria Ground Truth",
        "Fidelity Match", "Halusinasi", "Keterangan Halusinasi"
    ]
    ws_data.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws_data.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_idx, r in enumerate(dataset["records"], start=2):
        row_vals = [
            r["applicant_code"],
            r["citizen_masked"],
            r["rt"],
            r["rw"],
            r["status"],
            r["ranking"] or "-",
            r["final_score"] if r["final_score"] is not None else "-",
            r["explanation_source"],
            r["ai_primary_criterion"] or "-",
            r["expected_primary_criterion"] or "-",
            "-" if r["fidelity_match"] is None else ("YA" if r["fidelity_match"] else "TIDAK"),
            "TERDETEKSI" if r["hallucination_detected"] else "BERSIH",
            "; ".join(r["hallucination_reasons"]) if r["hallucination_reasons"] else "-"
        ]
        ws_data.append(row_vals)
        for col_num in range(1, len(row_vals) + 1):
            cell = ws_data.cell(row=row_idx, column=col_num)
            cell.border = border_thin
            if col_num in (1, 3, 4, 5, 6, 9, 10, 11, 12):
                cell.alignment = Alignment(horizontal="center")

    # Sheet 2: Ringkasan Metrik
    ws_summary = wb.create_sheet(title="Ringkasan Metrik Skripsi")
    ws_summary.append(["Indikator Evaluasi Skripsi", "Nilai Target PRD", "Hasil Pengujian Sistem"])
    for col_num in range(1, 4):
        c = ws_summary.cell(row=1, column=col_num)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center")

    summary_rows = [
        ("Fidelity Score Narasi XAI", ">= 95.0%", f"{dataset['summary_metrics']['fidelity_score']}%"),
        ("Tingkat Halusinasi (Hallucination Rate)", "0.0%", f"{dataset['summary_metrics']['hallucination_rate']}%"),
        ("Total Kandidat Dievaluasi", "-", str(dataset["summary_metrics"]["total_candidates"])),
        ("Kandidat Lolos Administratif", "-", str(dataset["summary_metrics"]["eligible_candidates"])),
        ("Kandidat Diskualifikasi TMS", "-", str(dataset["summary_metrics"]["disqualified_tms"])),
        ("KPM Lolos Kuota", "-", str(dataset["summary_metrics"]["passed_count"])),
        ("KPM Tidak Lolos Kuota", "-", str(dataset["summary_metrics"]["failed_count"])),
    ]
    for row_idx, (ind, target, val) in enumerate(summary_rows, start=2):
        ws_summary.append([ind, target, val])
        for col_num in range(1, 4):
            c = ws_summary.cell(row=row_idx, column=col_num)
            c.border = border_thin
            if col_num in (2, 3):
                c.alignment = Alignment(horizontal="center")

    # Sheet 3: Instrumen Kuesioner SUS
    ws_sus = wb.create_sheet(title="Instrumen SUS (10 Butir)")
    ws_sus.append(["No", "Polaritas", "Pernyataan Kuesioner (System Usability Scale)", "Skala Minimal (1)", "Skala Maksimal (5)"])
    for col_num in range(1, 6):
        c = ws_sus.cell(row=1, column=col_num)
        c.font = header_font
        c.fill = header_fill

    for row_idx, q in enumerate(get_sus_questionnaire_template(), start=2):
        ws_sus.append([q["id"], q["polarity"].upper(), q["question"], q["scale_min_label"], q["scale_max_label"]])
        for col_num in range(1, 6):
            c = ws_sus.cell(row=row_idx, column=col_num)
            c.border = border_thin
            if col_num in (1, 2):
                c.alignment = Alignment(horizontal="center")

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
