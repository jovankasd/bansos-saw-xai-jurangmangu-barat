"""
core/services/pdf_generator.py — Official PDF Document Generation Service.

PRD References:
  - Bagian 1 & 11: Berita Acara Penetapan Penerima Bansos (ReportLab, QR Code, Lampiran TMS).
  - Bagian 3 & UU PDP No. 27/2022: Controlled NIK Decryption ONLY for official Berita Acara PDF,
    with immutable logging to AuditLog (action=AuditLog.Action.NIK_DECRYPT).
  - Bagian 10.6 & FR-06: Individual Citizen Result PDF with strict PII masking (nik_masked, name_masked).
"""

from __future__ import annotations

import io
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.models import (
    AuditLog,
    Evaluation,
    SelectionBatch,
    SelectionResult,
)

# Civic Precision Palette Tokens
COLOR_PRIMARY = colors.HexColor("#003426")        # Emerald Civic Primary
COLOR_PRIMARY_CONTAINER = colors.HexColor("#0f4c3a")
COLOR_ACCENT = colors.HexColor("#1b6e54")
COLOR_TEXT_MAIN = colors.HexColor("#1e293b")
COLOR_TEXT_MUTED = colors.HexColor("#64748b")
COLOR_BORDER = colors.HexColor("#cbd5e1")
COLOR_BG_ALT = colors.HexColor("#f8fafc")
COLOR_SUCCESS = colors.HexColor("#15803d")
COLOR_WARN = colors.HexColor("#b45309")
COLOR_DANGER = colors.HexColor("#b91c1c")


def _generate_qr_flowable(data: str, size_mm: float = 28.0) -> Image:
    """Generate a ReportLab Image Flowable containing a QR Code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#003426", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return Image(buffer, width=size_mm * mm, height=size_mm * mm)


def _build_kop_surat(styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Build the official Kop Surat for Kelurahan Jurangmangu Barat."""
    elements = []
    kop_text_1 = Paragraph(
        "<b>PEMERINTAH KOTA TANGERANG SELATAN</b>",
        styles["KopCity"],
    )
    kop_text_2 = Paragraph(
        "<b>KECAMATAN PONDOK AREN</b>",
        styles["KopDistrict"],
    )
    kop_text_3 = Paragraph(
        "<b>KELURAHAN JURANGMANGU BARAT</b>",
        styles["KopSubdistrict"],
    )
    kop_address = Paragraph(
        "Jl. Raya Jurangmangu Barat No. 1, Pondok Aren, Kota Tangerang Selatan, Banten 15223<br/>"
        "Laman: kel-jurangmangubarat.tangerangselatankota.go.id | Pos-el: kelurahan.jmb@tangerangselatankota.go.id",
        styles["KopAddress"],
    )

    elements.extend([
        kop_text_1,
        kop_text_2,
        kop_text_3,
        Spacer(1, 1.5 * mm),
        kop_address,
        Spacer(1, 2 * mm),
        HRFlowable(width="100%", thickness=2.0, color=COLOR_PRIMARY, spaceBefore=1, spaceAfter=1),
        HRFlowable(width="100%", thickness=0.75, color=COLOR_PRIMARY, spaceBefore=0.5, spaceAfter=4 * mm),
    ])
    return elements


def generate_berita_acara_pdf(batch_id: int, performed_by: str = "system") -> bytes:
    """
    Generate the official Berita Acara Penetapan Penerima Bansos PDF.

    Security & Privacy (UU PDP No. 27/2022 & PRD Section 3):
      - Decrypts nik_encrypted for passed and TMS citizens ONLY within this official report.
      - Automatically creates an immutable AuditLog entry with action=NIK_DECRYPT.
      - Plaintext NIK is never leaked into audit log details or logs.
      - Includes official Kop Surat, Passed KPM ranking table, separate TMS Appendix,
        and QR Code verification.
    """
    batch = (
        SelectionBatch.objects.select_related("period", "created_by")
        .prefetch_related("evaluations__citizen", "evaluations__result")
        .get(pk=batch_id)
    )

    # 1. Fetch all evaluations
    evaluations = list(
        batch.evaluations.select_related("citizen", "result")
        .order_by("result__ranking", "id")
    )

    passed_evals = [
        e for e in evaluations
        if e.eligibility_status == Evaluation.EligibilityStatus.ELIGIBLE
        and hasattr(e, "result")
        and e.result
        and e.result.status == SelectionResult.ResultStatus.LOLOS
    ]
    # Sort passed evaluations strictly by ranking
    passed_evals.sort(key=lambda x: (x.result.ranking or 99999, -(x.result.final_score_v or Decimal(0))))

    tms_evals = [
        e for e in evaluations
        if e.eligibility_status == Evaluation.EligibilityStatus.DISQUALIFIED
    ]
    tms_evals.sort(key=lambda x: (x.citizen.rt, x.citizen.full_name))

    # 2. Controlled NIK Decryption & Audit Logging (UU PDP No. 27/2022)
    # Perform decryption for official legal report
    decrypted_records = {}
    for e in passed_evals:
        decrypted_records[e.id] = e.citizen.decrypt_nik()
    for e in tms_evals:
        decrypted_records[e.id] = e.citizen.decrypt_nik()

    # Immutable AuditLog creation (Strictly NO plaintext NIK in detail or fields)
    AuditLog.objects.create(
        batch=batch,
        action=AuditLog.Action.NIK_DECRYPT,
        performed_by=performed_by or "system",
        target_object_repr=f"SelectionBatch #{batch.id} ({batch.name})",
        detail=f"Dekripsi NIK terkontrol untuk penerbitan Berita Acara PDF resmi (Total: {len(decrypted_records)} warga)",
    )

    # 3. Setup ReportLab Document
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    # Styles
    base_styles = getSampleStyleSheet()
    styles = {
        "KopCity": ParagraphStyle(
            "KopCity",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=13,
            alignment=1,  # Center
            textColor=COLOR_TEXT_MAIN,
        ),
        "KopDistrict": ParagraphStyle(
            "KopDistrict",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=15,
            alignment=1,
            textColor=COLOR_TEXT_MAIN,
        ),
        "KopSubdistrict": ParagraphStyle(
            "KopSubdistrict",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            alignment=1,
            textColor=COLOR_PRIMARY,
        ),
        "KopAddress": ParagraphStyle(
            "KopAddress",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=COLOR_TEXT_MUTED,
        ),
        "DocTitle": ParagraphStyle(
            "DocTitle",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=1,
            textColor=COLOR_PRIMARY,
        ),
        "DocDocNum": ParagraphStyle(
            "DocDocNum",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            alignment=1,
            textColor=COLOR_TEXT_MAIN,
        ),
        "BodyText": ParagraphStyle(
            "BodyText",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=COLOR_TEXT_MAIN,
            alignment=4,  # Justify
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10.5,
            alignment=1,
            textColor=colors.white,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=COLOR_TEXT_MAIN,
        ),
        "TableCellCenter": ParagraphStyle(
            "TableCellCenter",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=COLOR_TEXT_MAIN,
        ),
        "TableCellMono": ParagraphStyle(
            "TableCellMono",
            parent=base_styles["Normal"],
            fontName="Courier",
            fontSize=7.5,
            leading=9.5,
            alignment=1,
            textColor=COLOR_TEXT_MAIN,
        ),
        "SectionHeader": ParagraphStyle(
            "SectionHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=COLOR_PRIMARY,
        ),
        "SignTitle": ParagraphStyle(
            "SignTitle",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=1,
            textColor=COLOR_TEXT_MAIN,
        ),
        "SignName": ParagraphStyle(
            "SignName",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,
            textColor=COLOR_TEXT_MAIN,
        ),
        "SignNip": ParagraphStyle(
            "SignNip",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=COLOR_TEXT_MUTED,
        ),
    }

    elements = []

    # 1. Kop Surat
    elements.extend(_build_kop_surat(styles))

    # 2. Document Title & Number
    year = batch.period.year if hasattr(batch.period, "year") else timezone.now().year
    doc_number = f"BA/{batch.id:03d}/BANSOS-JMB/{year}"
    elements.extend([
        Paragraph("<b>BERITA ACARA HASIL SELEKSI PENETAPAN PENERIMA BANTUAN SOSIAL</b>", styles["DocTitle"]),
        Spacer(1, 1 * mm),
        Paragraph(f"Nomor: {doc_number}", styles["DocDocNum"]),
        Spacer(1, 4 * mm),
    ])

    # 3. Preamble Narrative
    date_str = timezone.now().strftime("%d %B %Y")
    calc_date_str = (batch.calculated_at or timezone.now()).strftime("%d %B %Y")
    preamble = (
        f"Pada hari ini bertempat di Kantor Kelurahan Jurangmangu Barat, telah diselenggarakan "
        f"sidang musyawarah penetapan penerima program <b>{batch.period.name}</b> ({batch.name}). "
        f"Penetapan ini didasarkan pada perankingan objektif Sistem Pendukung Keputusan menggunakan "
        f"metode <i>Simple Additive Weighting</i> (SAW) tertanggal {calc_date_str}, dengan alokasi kuota "
        f"sebanyak <b>{batch.quota} penerima manfaat</b> dari total {len(evaluations)} data calon KPM yang diusulkan."
    )
    elements.extend([
        Paragraph(preamble, styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("<b>I. DAFTAR PENERIMA MANFAAT YANG DITETAPKAN LOLOS KUOTA</b>", styles["SectionHeader"]),
        Spacer(1, 2 * mm),
    ])

    # 4. Table: Passed KPMs
    table_data = [
        [
            Paragraph("<b>No</b>", styles["TableHeader"]),
            Paragraph("<b>Nomor Induk Kependudukan (NIK)</b>", styles["TableHeader"]),
            Paragraph("<b>Nama Lengkap</b>", styles["TableHeader"]),
            Paragraph("<b>RT/RW</b>", styles["TableHeader"]),
            Paragraph("<b>Skor SAW (V)</b>", styles["TableHeader"]),
            Paragraph("<b>Peringkat</b>", styles["TableHeader"]),
            Paragraph("<b>Status</b>", styles["TableHeader"]),
        ]
    ]

    if passed_evals:
        for idx, eval_obj in enumerate(passed_evals, start=1):
            nik_plain = decrypted_records.get(eval_obj.id, eval_obj.citizen.nik_masked)
            score_v = f"{float(eval_obj.result.final_score_v):.4f}" if eval_obj.result.final_score_v is not None else "-"
            table_data.append([
                Paragraph(str(idx), styles["TableCellCenter"]),
                Paragraph(nik_plain, styles["TableCellMono"]),
                Paragraph(eval_obj.citizen.full_name, styles["TableCell"]),
                Paragraph(f"{eval_obj.citizen.rt}/{eval_obj.citizen.rw}", styles["TableCellCenter"]),
                Paragraph(score_v, styles["TableCellCenter"]),
                Paragraph(str(eval_obj.result.ranking or idx), styles["TableCellCenter"]),
                Paragraph("<b>LOLOS</b>", styles["TableCellCenter"]),
            ])
    else:
        table_data.append([
            Paragraph("1", styles["TableCellCenter"]),
            Paragraph("-", styles["TableCellCenter"]),
            Paragraph("(Tidak ada calon KPM yang lolos alokasi kuota)", styles["TableCell"]),
            Paragraph("-", styles["TableCellCenter"]),
            Paragraph("-", styles["TableCellCenter"]),
            Paragraph("-", styles["TableCellCenter"]),
            Paragraph("-", styles["TableCellCenter"]),
        ])

    col_widths = [10 * mm, 38 * mm, 50 * mm, 18 * mm, 24 * mm, 18 * mm, 22 * mm]
    main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    main_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_BG_ALT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(main_table)
    elements.append(Spacer(1, 5 * mm))

    # 5. Signatures & QR Code Section
    qr_data = (
        f"DOKUMEN RESMI KELURAHAN JURANGMANGU BARAT\n"
        f"Nomor: {doc_number}\n"
        f"Batch ID: {batch.id}\n"
        f"Periode: {batch.period.name}\n"
        f"Penerima Lolos: {len(passed_evals)} KPM\n"
        f"Status: {batch.status}\n"
        f"Pengesahan: {batch.approved_by or 'Lurah Jurangmangu Barat'}\n"
        f"Verifikasi: https://bansos.jurangmangubarat.id/verify/{batch.id}"
    )
    qr_flowable = _generate_qr_flowable(qr_data, size_mm=26.0)

    # Table layout for signatures and QR code
    sig_cell_left = [
        Paragraph("Mengetahui,<br/><b>Lurah Jurangmangu Barat</b>", styles["SignTitle"]),
        Spacer(1, 16 * mm),
        Paragraph("<u><b>H. Ahmad Syarif</b></u>", styles["SignName"]),
        Paragraph("NIP. 19760822 199903 1 002", styles["SignNip"]),
    ]
    sig_cell_right = [
        Paragraph(f"Tangerang Selatan, {date_str}<br/><b>Kasi Kesejahteraan Sosial</b>", styles["SignTitle"]),
        Spacer(1, 16 * mm),
        Paragraph("<u><b>Budi Hartono, S.Sos</b></u>", styles["SignName"]),
        Paragraph("NIP. 19820514 200801 1 004", styles["SignNip"]),
    ]
    qr_cell = [
        qr_flowable,
        Spacer(1, 1 * mm),
        Paragraph("<font size=6 color='#64748b'>Pindai untuk verifikasi keaslian Berita Acara</font>", styles["TableCellCenter"]),
    ]

    sig_table = Table(
        [[sig_cell_left, qr_cell, sig_cell_right]],
        colWidths=[65 * mm, 50 * mm, 65 * mm],
    )
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(KeepTogether(sig_table))

    # 6. Page Break & Appendix: TMS (Disqualified) Candidates
    elements.append(PageBreak())
    elements.extend(_build_kop_surat(styles))

    elements.extend([
        Paragraph("<b>LAMPIRAN I: DAFTAR USULAN TIDAK MEMENUHI SYARAT (TMS)</b>", styles["DocTitle"]),
        Spacer(1, 1 * mm),
        Paragraph(f"Lampiran Berita Acara Nomor: {doc_number}", styles["DocDocNum"]),
        Spacer(1, 3 * mm),
        Paragraph(
            "Berdasarkan hasil verifikasi kriteria pengecualian mutlak (FR-02), warga di bawah ini "
            "dikeluarkan dari matriks perhitungan normalisasi SAW untuk menjamin objektivitas seleksi:",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
    ])

    tms_table_data = [
        [
            Paragraph("<b>No</b>", styles["TableHeader"]),
            Paragraph("<b>Nomor Induk Kependudukan (NIK)</b>", styles["TableHeader"]),
            Paragraph("<b>Nama Lengkap</b>", styles["TableHeader"]),
            Paragraph("<b>RT/RW</b>", styles["TableHeader"]),
            Paragraph("<b>Alasan Diskualifikasi (TMS)</b>", styles["TableHeader"]),
        ]
    ]

    if tms_evals:
        for idx, eval_obj in enumerate(tms_evals, start=1):
            nik_plain = decrypted_records.get(eval_obj.id, eval_obj.citizen.nik_masked)
            tms_label = eval_obj.get_tms_reason_display() if hasattr(eval_obj, "get_tms_reason_display") else (eval_obj.tms_reason or "Tidak Memenuhi Syarat")
            tms_table_data.append([
                Paragraph(str(idx), styles["TableCellCenter"]),
                Paragraph(nik_plain, styles["TableCellMono"]),
                Paragraph(eval_obj.citizen.full_name, styles["TableCell"]),
                Paragraph(f"{eval_obj.citizen.rt}/{eval_obj.citizen.rw}", styles["TableCellCenter"]),
                Paragraph(f"<b>{tms_label}</b>", styles["TableCellCenter"]),
            ])
    else:
        tms_table_data.append([
            Paragraph("1", styles["TableCellCenter"]),
            Paragraph("-", styles["TableCellCenter"]),
            Paragraph("(Tidak ada usulan berstatus TMS pada periode seleksi ini)", styles["TableCell"]),
            Paragraph("-", styles["TableCellCenter"]),
            Paragraph("-", styles["TableCellCenter"]),
        ])

    tms_col_widths = [10 * mm, 45 * mm, 60 * mm, 20 * mm, 45 * mm]
    tms_table = Table(tms_table_data, colWidths=tms_col_widths, repeatRows=1)
    tms_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY_CONTAINER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_BG_ALT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(tms_table)
    elements.append(Spacer(1, 8 * mm))

    # Appendix Signature
    app_sig_table = Table(
        [[
            "",
            [
                Paragraph(f"Tangerang Selatan, {date_str}<br/><b>Lurah Jurangmangu Barat</b>", styles["SignTitle"]),
                Spacer(1, 16 * mm),
                Paragraph("<u><b>H. Ahmad Syarif</b></u>", styles["SignName"]),
                Paragraph("NIP. 19760822 199903 1 002", styles["SignNip"]),
            ]
        ]],
        colWidths=[100 * mm, 80 * mm],
    )
    elements.append(KeepTogether(app_sig_table))

    # Build PDF
    doc.build(elements)
    return buffer.getvalue()


def generate_individual_result_pdf(evaluation_id: int) -> bytes:
    """
    Generate the official individual citizen result notification PDF.
    Designed for citizen download via the public portal (/cek-bansos).

    Security & Privacy (UU PDP No. 27/2022 & PRD Section 10.6):
      - Strictly masks NIK and full name (nik_masked, full_name_masked).
      - NEVER decrypts NIK into plaintext.
      - Includes transparent SAW ranking and XAI narrative breakdown.
    """
    eval_obj = (
        Evaluation.objects.select_related("citizen", "batch__period", "result")
        .prefetch_related("details__criteria")
        .get(pk=evaluation_id)
    )
    citizen = eval_obj.citizen
    batch = eval_obj.batch
    result_obj = getattr(eval_obj, "result", None)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    base_styles = getSampleStyleSheet()
    styles = {
        "KopCity": ParagraphStyle("KopCity", parent=base_styles["Normal"], fontName="Helvetica", fontSize=10, leading=12, alignment=1, textColor=COLOR_TEXT_MAIN),
        "KopDistrict": ParagraphStyle("KopDistrict", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=14, alignment=1, textColor=COLOR_TEXT_MAIN),
        "KopSubdistrict": ParagraphStyle("KopSubdistrict", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=13, leading=15, alignment=1, textColor=COLOR_PRIMARY),
        "KopAddress": ParagraphStyle("KopAddress", parent=base_styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=9.5, alignment=1, textColor=COLOR_TEXT_MUTED),
        "DocTitle": ParagraphStyle("DocTitle", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=15, alignment=1, textColor=COLOR_PRIMARY),
        "DocDocNum": ParagraphStyle("DocDocNum", parent=base_styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, alignment=1, textColor=COLOR_TEXT_MUTED),
        "BodyText": ParagraphStyle("BodyText", parent=base_styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=COLOR_TEXT_MAIN, alignment=4),
        "SectionHeader": ParagraphStyle("SectionHeader", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=COLOR_PRIMARY),
        "CardLabel": ParagraphStyle("CardLabel", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=COLOR_TEXT_MUTED),
        "CardValue": ParagraphStyle("CardValue", parent=base_styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=COLOR_TEXT_MAIN),
        "StatusBadgeLolos": ParagraphStyle("StatusBadgeLolos", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=14, alignment=1, textColor=COLOR_SUCCESS),
        "StatusBadgeTidakLolos": ParagraphStyle("StatusBadgeTidakLolos", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=14, alignment=1, textColor=COLOR_WARN),
        "StatusBadgeTms": ParagraphStyle("StatusBadgeTms", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=14, alignment=1, textColor=COLOR_DANGER),
        "TableHeader": ParagraphStyle("TableHeader", parent=base_styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=1, textColor=colors.white),
        "TableCellCenter": ParagraphStyle("TableCellCenter", parent=base_styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=9.5, alignment=1, textColor=COLOR_TEXT_MAIN),
        "TableCellLeft": ParagraphStyle("TableCellLeft", parent=base_styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=COLOR_TEXT_MAIN),
        "Footnote": ParagraphStyle("Footnote", parent=base_styles["Normal"], fontName="Helvetica", fontSize=7, leading=9, alignment=1, textColor=COLOR_TEXT_MUTED),
    }

    elements = []
    # 1. Kop Surat
    elements.extend(_build_kop_surat(styles))

    # 2. Document Title
    reg_code = f"KPM-{eval_obj.id:04d}"
    elements.extend([
        Paragraph("<b>SURAT PEMBERITAHUAN HASIL SELEKSI BANTUAN SOSIAL</b>", styles["DocTitle"]),
        Spacer(1, 1 * mm),
        Paragraph(f"Nomor Registrasi: {reg_code} | Periode: {batch.period.name}", styles["DocDocNum"]),
        Spacer(1, 3.5 * mm),
    ])

    # 3. Applicant Data & Result Summary Card
    status_label = result_obj.status if result_obj else ("DISKUALIFIKASI_TMS" if eval_obj.eligibility_status == "DISQUALIFIED" else "PROSES")
    if status_label == "LOLOS":
        status_style = styles["StatusBadgeLolos"]
        status_box_bg = colors.HexColor("#f0fdf4")
    elif status_label == "TIDAK_LOLOS":
        status_style = styles["StatusBadgeTidakLolos"]
        status_box_bg = colors.HexColor("#fffbeb")
    else:
        status_style = styles["StatusBadgeTms"]
        status_box_bg = colors.HexColor("#fef2f2")

    rank_str = f"Peringkat {result_obj.ranking} dari Kuota {batch.quota}" if (result_obj and result_obj.ranking) else f"Kuota {batch.quota}"
    score_str = f"{float(result_obj.final_score_v):.4f}" if (result_obj and result_obj.final_score_v is not None) else "-"
    cutoff_str = f"{float(batch.cutoff_score):.4f}" if batch.cutoff_score is not None else "-"

    card_data = [
        [
            Paragraph("<b>DATA PEMOHON</b>", styles["CardLabel"]),
            "",
            Paragraph("<b>HASIL KELAYAKAN SELEKSI</b>", styles["CardLabel"]),
            "",
        ],
        [
            Paragraph("Nama Pemohon:", styles["CardLabel"]),
            Paragraph(f"<b>{citizen.full_name_masked}</b>", styles["CardValue"]),
            Paragraph("Status Seleksi:", styles["CardLabel"]),
            Paragraph(f"<b>{status_label.replace('_', ' ')}</b>", status_style),
        ],
        [
            Paragraph("Nomor Induk (NIK):", styles["CardLabel"]),
            Paragraph(f'<font name="Courier">{citizen.nik_masked}</font>', styles["CardValue"]),
            Paragraph("Pemeringkatan:", styles["CardLabel"]),
            Paragraph(rank_str, styles["CardValue"]),
        ],
        [
            Paragraph("Domisili RT/RW:", styles["CardLabel"]),
            Paragraph(f"RT {citizen.rt} / RW {citizen.rw}", styles["CardValue"]),
            Paragraph("Skor Preferensi (V):", styles["CardLabel"]),
            Paragraph(f"<b>{score_str}</b> (Batas Cut-off: {cutoff_str})", styles["CardValue"]),
        ],
    ]

    card_table = Table(card_data, colWidths=[38 * mm, 50 * mm, 42 * mm, 50 * mm])
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_ALT),
        ("BACKGROUND", (2, 1), (3, 1), status_box_bg),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (2, 0), (3, 0)),
    ]))
    elements.append(card_table)
    elements.append(Spacer(1, 4 * mm))

    # 4. Transparent Explanation & Narrative (XAI)
    raw_ai = result_obj.ai_payload_response if (result_obj and isinstance(result_obj.ai_payload_response, dict)) else {}
    summary_text = (
        raw_ai.get("ringkasan_keputusan")
        or raw_ai.get("ringkasan")
        or result_obj.ai_narrative
        or "Penetapan hasil seleksi didasarkan pada perankingan terbobot multi-kriteria."
    )
    factors = raw_ai.get("faktor_penentu_utama") or raw_ai.get("faktor_utama") or []
    full_narrative = result_obj.ai_narrative or ""
    rec_text = (
        raw_ai.get("rekomendasi_tindak_lanjut")
        or raw_ai.get("rekomendasi")
        or "Silakan berkoordinasi dengan Ketua RT setempat untuk pemutakhiran data kependudukan."
    )

    narrative_paragraphs = [
        Paragraph("<b>PENJELASAN TRANSPARANSI KEPUTUSAN (EXPLAINABLE AI)</b>", styles["SectionHeader"]),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Ringkasan:</b> {summary_text}", styles["BodyText"]),
    ]

    if factors:
        factor_items = "<br/>".join([f"&bull; {str(f)}" for f in factors])
        narrative_paragraphs.extend([
            Spacer(1, 1 * mm),
            Paragraph(f"<b>Faktor Penentu Utama:</b><br/>{factor_items}", styles["BodyText"]),
        ])

    if full_narrative and full_narrative != summary_text:
        narrative_paragraphs.extend([
            Spacer(1, 1 * mm),
            Paragraph(f"<b>Catatan Hasil Evaluasi:</b> {full_narrative}", styles["BodyText"]),
        ])

    narrative_paragraphs.extend([
        Spacer(1, 1 * mm),
        Paragraph(f"<b>Rekomendasi Tindak Lanjut:</b> {rec_text}", styles["BodyText"]),
    ])

    elements.extend(narrative_paragraphs)
    elements.append(Spacer(1, 4 * mm))

    # 5. Criteria Comparison Table
    elements.append(Paragraph("<b>MATRIKS EVALUASI KRITERIA TERBOBOT</b>", styles["SectionHeader"]))
    elements.append(Spacer(1, 1.5 * mm))

    crit_table_data = [
        [
            Paragraph("<b>Kode</b>", styles["TableHeader"]),
            Paragraph("<b>Nama Kriteria</b>", styles["TableHeader"]),
            Paragraph("<b>Tipe</b>", styles["TableHeader"]),
            Paragraph("<b>Bobot</b>", styles["TableHeader"]),
            Paragraph("<b>Nilai Pemohon (r_ij)</b>", styles["TableHeader"]),
            Paragraph("<b>Rata-rata Lolos</b>", styles["TableHeader"]),
        ]
    ]

    if isinstance(raw_ai, dict) and "criteria_data" in raw_ai:
        for c in raw_ai["criteria_data"]:
            crit_table_data.append([
                Paragraph(str(c.get("code", "-")), styles["TableCellCenter"]),
                Paragraph(str(c.get("name", "-")), styles["TableCellLeft"]),
                Paragraph(str(c.get("type", "-")), styles["TableCellCenter"]),
                Paragraph(f"{float(c.get('weight', 0)):.2f}", styles["TableCellCenter"]),
                Paragraph(f"{float(c.get('normalized_score', 0)):.4f}", styles["TableCellCenter"]),
                Paragraph(f"{float(c.get('avg_passed_score', 0)):.4f}", styles["TableCellCenter"]),
            ])
    else:
        for det in eval_obj.details.select_related("criteria").all():
            crit_table_data.append([
                Paragraph(det.criteria.code, styles["TableCellCenter"]),
                Paragraph(det.criteria.name, styles["TableCellLeft"]),
                Paragraph(det.criteria.criterion_type, styles["TableCellCenter"]),
                Paragraph(f"{float(det.criteria.weight):.2f}", styles["TableCellCenter"]),
                Paragraph(f"{float(det.normalized_value or 0):.4f}", styles["TableCellCenter"]),
                Paragraph("-", styles["TableCellCenter"]),
            ])

    crit_table = Table(crit_table_data, colWidths=[15 * mm, 55 * mm, 25 * mm, 20 * mm, 32 * mm, 33 * mm])
    crit_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_BG_ALT]),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(crit_table)
    elements.append(Spacer(1, 5 * mm))

    # 6. Verification QR & Footer
    qr_data = (
        f"HASIL RESMI SELEKSI BANSOS JURANGMANGU BARAT\n"
        f"Registrasi: {reg_code}\n"
        f"NIK Masked: {citizen.nik_masked}\n"
        f"Status: {status_label}\n"
        f"Peringkat: {result_obj.ranking if result_obj else '-'}\n"
        f"Periode: {batch.period.name}\n"
        f"Verifikasi: https://bansos.jurangmangubarat.id/cek-bansos"
    )
    qr_flowable = _generate_qr_flowable(qr_data, size_mm=22.0)

    qr_block = Table(
        [[
            qr_flowable,
            [
                Paragraph("<b>TANDA BUKTI ELEKTRONIK RESMI</b>", styles["CardLabel"]),
                Paragraph(
                    "Dokumen ini diterbitkan secara otomatis dan sah oleh Sistem Pendukung Keputusan "
                    "Kelurahan Jurangmangu Barat untuk keperluan transparansi publik warga. "
                    "Keabsahan informasi dapat diverifikasi secara daring pada portal resmi kelurahan.",
                    styles["Footnote"],
                ),
            ]
        ]],
        colWidths=[28 * mm, 152 * mm],
    )
    qr_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(KeepTogether(qr_block))

    doc.build(elements)
    return buffer.getvalue()
