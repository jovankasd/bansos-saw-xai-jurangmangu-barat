"""
backend/core/services/excel_ingest.py — Excel Batch Import & Recapitulation Export.

Provides:
  1. import_citizens_from_excel(file_obj, batch_id, user) -> dict
     - Parses .xlsx files with row-level error reporting.
     - Enforces UU PDP No. 27/2022 (create_or_update_with_nik).
     - Enforces Surveyor RT scoping (only import rows matching surveyor.rt_number).
     - Deduplicates by NIK hash within batch.
  2. export_batch_results_xlsx(batch_id) -> bytes
     - Exports formatted Excel recapitulation of SAW ranking & XAI summaries.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from django.core.exceptions import ValidationError
from django.db import transaction

from core.crypto import hash_nik, validate_nik
from core.models import (
    AuditLog,
    Citizen,
    Criteria,
    Evaluation,
    EvaluationDetail,
    SelectionBatch,
    SelectionResult,
    StaffUser,
)
from core.permissions import check_surveyor_rt_scope, normalize_rt

logger = logging.getLogger(__name__)


def import_citizens_from_excel(
    file_obj,
    batch_id: int,
    user: StaffUser | None = None,
) -> Dict[str, Any]:
    """
    Imports citizen data and evaluations from an uploaded Excel (.xlsx) file.
    Returns:
        {
            "total_imported": int,
            "duplicates_skipped": int,
            "errors": [{"row": int, "error": str}],
        }
    """
    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        ws = wb.active
    except Exception as exc:
        raise ValidationError(f"File Excel tidak valid atau rusak: {exc}")

    try:
        batch = SelectionBatch.objects.get(id=batch_id)
    except SelectionBatch.DoesNotExist:
        raise ValidationError(f"Batch seleksi dengan ID {batch_id} tidak ditemukan.")

    if batch.status not in (SelectionBatch.Status.DRAFT, SelectionBatch.Status.COLLECTING):
        raise ValidationError(
            f"Pendaftaran usulan warga hanya dapat dilakukan pada batch berstatus 'Draft' atau 'Collecting' "
            f"(Status saat ini: {batch.status})."
        )

    # Load master criteria
    criteria_map = {c.code.upper(): c for c in Criteria.objects.all()}

    header_row = [str(cell.value).strip().lower() if cell.value is not None else "" for cell in ws[1]]
    
    # Helper to find column index (0-based)
    def find_col(*aliases: str) -> int:
        for idx, h in enumerate(header_row):
            for a in aliases:
                if a in h:
                    return idx
        return -1

    idx_nik = find_col("nik")
    idx_name = find_col("nama", "name")
    idx_kk = find_col("kk", "4 digit")
    idx_rt = find_col("rt")
    idx_rw = find_col("rw")
    idx_addr = find_col("alamat", "address")
    idx_status = find_col("status", "kelayakan")
    idx_tms = find_col("alasan", "tms")
    idx_dep = find_col("tanggungan riil", "tanggungan", "dependents")
    idx_c1 = find_col("c1", "pendapatan")
    idx_c2 = find_col("c2", "tanggungan")
    idx_c3 = find_col("c3", "rumah", "tempat tinggal")
    idx_c4 = find_col("c4", "aset")

    total_imported = 0
    duplicates_skipped = 0
    errors: List[Dict[str, Any]] = []
    seen_in_file: set[str] = set()

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row_idx > 1001:
            errors.append({"row": row_idx, "error": "Batas maksimum 1.000 baris per batch import terlampaui."})
            break

        # Stop at empty row
        if not any(row):
            continue

        raw_nik = str(row[idx_nik]).strip() if idx_nik >= 0 and row[idx_nik] is not None else ""
        raw_name = str(row[idx_name]).strip() if idx_name >= 0 and row[idx_name] is not None else ""
        raw_kk = str(row[idx_kk]).strip() if idx_kk >= 0 and row[idx_kk] is not None else "0000"
        raw_rt = str(row[idx_rt]).strip() if idx_rt >= 0 and row[idx_rt] is not None else "001"
        raw_rw = str(row[idx_rw]).strip() if idx_rw >= 0 and row[idx_rw] is not None else "001"
        raw_addr = str(row[idx_addr]).strip() if idx_addr >= 0 and row[idx_addr] is not None else "Jurangmangu Barat"
        raw_status = str(row[idx_status]).strip().upper() if idx_status >= 0 and row[idx_status] is not None else "ELIGIBLE"
        raw_tms = str(row[idx_tms]).strip().upper() if idx_tms >= 0 and row[idx_tms] is not None else ""
        
        # Real dependents
        try:
            real_dep = int(row[idx_dep]) if idx_dep >= 0 and row[idx_dep] is not None else 0
        except (ValueError, TypeError):
            real_dep = 0

        # Validate NIK
        # Excel might read large numbers as floats or scientific notation (e.g. 3.67403E+15)
        if "." in raw_nik:
            try:
                raw_nik = str(int(float(raw_nik)))
            except Exception:
                pass
        raw_nik = raw_nik.split(".")[0]

        if not raw_nik or len(raw_nik) != 16 or not raw_nik.isdigit():
            errors.append({"row": row_idx, "error": f"NIK '{raw_nik}' tidak valid (wajib 16 digit angka)."})
            continue

        # Clean KK last 4
        if "." in raw_kk:
            raw_kk = raw_kk.split(".")[0]
        raw_kk = raw_kk.zfill(4)[-4:]

        # Surveyor scope check
        if user and not check_surveyor_rt_scope(user, raw_rt):
            errors.append({
                "row": row_idx,
                "error": f"RT {raw_rt} berada di luar wilayah wewenang surveyor (RT {user.rt_number}).",
            })
            continue

        nik_digest = hash_nik(raw_nik)
        if nik_digest in seen_in_file:
            duplicates_skipped += 1
            continue
        seen_in_file.add(nik_digest)

        # Prevent cross-RT citizen overwrite if citizen is already registered in another RT
        existing_citizen = Citizen.objects.filter(nik_hash=nik_digest).first()
        if existing_citizen and user and user.role == StaffUser.Role.SURVEYOR:
            if normalize_rt(existing_citizen.rt) != normalize_rt(user.rt_number):
                errors.append({
                    "row": row_idx,
                    "error": (
                        f"Warga dengan NIK tersebut telah terdaftar di RT {existing_citizen.rt}. "
                        f"Surveyor RT {user.rt_number} tidak berwenang memodifikasi data warga wilayah lain."
                    ),
                })
                continue

        # Check if citizen already exists in this batch
        if Evaluation.objects.filter(batch=batch, citizen__nik_hash=nik_digest).exists():
            duplicates_skipped += 1
            continue

        # Crips values
        crips_dict = {}
        for c_code, col_idx in [("C1", idx_c1), ("C2", idx_c2), ("C3", idx_c3), ("C4", idx_c4)]:
            if col_idx >= 0 and row[col_idx] is not None:
                try:
                    val = int(row[col_idx])
                    crips_dict[c_code] = max(1, min(5, val))
                except (ValueError, TypeError):
                    crips_dict[c_code] = 1
            else:
                crips_dict[c_code] = 1

        # Normalize status & TMS reason
        eligibility = "DISQUALIFIED" if "DISQUALIFIED" in raw_status or "TMS" in raw_status else "ELIGIBLE"
        tms_reason = ""
        if eligibility == "DISQUALIFIED":
            if "ASN" in raw_tms:
                tms_reason = "ASN"
            elif "PKH" in raw_tms:
                tms_reason = "PKH_GANDA"
            elif "PINDAH" in raw_tms:
                tms_reason = "PINDAH"
            elif "MENINGGAL" in raw_tms:
                tms_reason = "MENINGGAL"
            else:
                tms_reason = "ASN"

        try:
            with transaction.atomic():
                citizen, _ = Citizen.objects.create_or_update_with_nik(
                    raw_nik=raw_nik,
                    kk_last4=raw_kk,
                    full_name=raw_name or f"Warga NIK {raw_nik[-4:]}",
                    address=raw_addr,
                    rt=normalize_rt(raw_rt),
                    rw=normalize_rt(raw_rw),
                )

                eval_obj = Evaluation.objects.create(
                    batch=batch,
                    citizen=citizen,
                    eligibility_status=eligibility,
                    tms_reason=tms_reason,
                    real_dependents_count=real_dep,
                )

                for c_code, crips_val in crips_dict.items():
                    if c_code in criteria_map:
                        EvaluationDetail.objects.create(
                            evaluation=eval_obj,
                            criteria=criteria_map[c_code],
                            crips_value=crips_val,
                        )

                total_imported += 1
        except Exception as exc:
            logger.error("Error inserting row %d: %s", row_idx, exc)
            errors.append({"row": row_idx, "error": str(exc)})

    # Audit log
    AuditLog.objects.create(
        batch=batch,
        action="EXCEL_IMPORT",
        actor=user.username if user else "system",
        notes=f"Imported {total_imported} KPM from Excel, {duplicates_skipped} duplicates skipped, {len(errors)} errors.",
    )

    return {
        "total_imported": total_imported,
        "duplicates_skipped": duplicates_skipped,
        "errors": errors,
    }


def export_batch_results_xlsx(batch_id: int) -> bytes:
    """
    Exports a structured Excel (.xlsx) file containing selection results,
    rankings, preference values, criteria inputs, and XAI summaries.
    """
    try:
        batch = SelectionBatch.objects.get(id=batch_id)
    except SelectionBatch.DoesNotExist:
        raise ValidationError(f"Batch seleksi #{batch_id} tidak ditemukan.")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Rekapitulasi Batch {batch.id}"

    headers = [
        "Peringkat",
        "Status",
        "NIK (Tersamar)",
        "Nama Lengkap (Tersamar)",
        "RT",
        "RW",
        "Nilai Preferensi (V)",
        "Tanggungan Riil",
        "C1 (Pendapatan)",
        "C2 (Tanggungan)",
        "C3 (Rumah)",
        "C4 (Aset)",
        "Level Tie-Break",
        "Sumber Narasi",
        "Ringkasan Narasi XAI",
    ]

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="003426", end_color="003426", fill_type="solid")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center

    # Query evaluations and their results
    evaluations = (
        batch.evaluations.select_related("citizen", "result")
        .prefetch_related("details__criteria")
        .all()
    )

    # Sort: LOLOS first by rank, then TIDAK_LOLOS by rank, then DISQUALIFIED
    def sort_key(e: Evaluation):
        res = getattr(e, "result", None)
        if not res:
            return (99, 9999)
        status_order = {"LOLOS": 1, "TIDAK_LOLOS": 2, "DISKUALIFIKASI_TMS": 3}
        return (status_order.get(res.status, 9), res.ranking or 9999)

    sorted_evals = sorted(evaluations, key=sort_key)

    for e in sorted_evals:
        res = getattr(e, "result", None)
        details_map = {d.criteria.code: d.crips_value for d in e.details.all()}

        rank = res.ranking if res and res.ranking else "-"
        status = res.status if res else e.eligibility_status
        score_v = f"{float(res.final_score_v):.4f}" if res and res.final_score_v is not None else "-"
        tie_lvl = res.tie_break_level if res else 0
        src = res.explanation_source if res else "-"
        narrative = (
            (res.ai_payload_response.get("ringkasan") or res.ai_narrative or "")
            if res and isinstance(res.ai_payload_response, dict)
            else (res.ai_narrative if res else "")
        )

        ws.append([
            rank,
            status,
            e.citizen.nik_masked,
            e.citizen.full_name_masked,
            e.citizen.rt,
            e.citizen.rw,
            score_v,
            e.real_dependents_count,
            details_map.get("C1", "-"),
            details_map.get("C2", "-"),
            details_map.get("C3", "-"),
            details_map.get("C4", "-"),
            tie_lvl,
            src,
            narrative,
        ])

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 45)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
