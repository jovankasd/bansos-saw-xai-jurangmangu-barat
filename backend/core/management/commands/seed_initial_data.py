"""
management/commands/seed_initial_data.py

Seeds the database with:
  - C1 Pendapatan Keluarga (COST, 0.30)
  - C2 Jumlah Tanggungan (BENEFIT, 0.25)
  - C3 Kondisi Tempat Tinggal (COST, 0.25)
  - C4 Kepemilikan Aset (COST, 0.20)
  - SubCriteria (Crips 1–5) for each criterion
  - Demo staff accounts (SuperAdmin, Surveyor RT-003, Viewer/Lurah)
  - One audit log entry marking the seed operation

Idempotent: safe to run multiple times; uses get_or_create / update_or_create.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import AuditLog, Criteria, Period, SelectionBatch, StaffUser, SubCriteria


# ---------------------------------------------------------------------------
# Criteria seed data (PRD §5 & §8.1 — AGENTS.md constraints, C1-C4)
# For COST criteria (C1, C3, C4), smaller Crips value (1) = lowest cost / highest
# social assistance priority so r_ij = min(X_j) / X_ij yields 1.00 for Crips 1.
# For BENEFIT criteria (C2), larger Crips value (5) = highest priority so
# r_ij = X_ij / max(X_j) yields 1.00 for Crips 5.
# ---------------------------------------------------------------------------

CRITERIA_DATA = [
    {
        "code": "C1",
        "name": "Pendapatan Keluarga",
        "criterion_type": "COST",
        "weight": Decimal("0.30"),
        "order": 1,
        "subcriteria": [
            (1, "Sangat Rendah (<= Rp 500.000/bln)", "Pendapatan keluarga di bawah atau sama dengan Rp 500.000 per bulan"),
            (2, "Rendah (Rp 500.001 - Rp 1.500.000/bln)", "Pendapatan keluarga Rp 500.001-1.500.000 per bulan"),
            (3, "Sedang (Rp 1.500.001 - Rp 2.500.000/bln)", "Pendapatan keluarga Rp 1.500.001-2.500.000 per bulan"),
            (4, "Tinggi (Rp 2.500.001 - Rp 4.000.000/bln)", "Pendapatan keluarga Rp 2.500.001-4.000.000 per bulan"),
            (5, "Sangat Tinggi (> Rp 4.000.000/bln)", "Pendapatan keluarga di atas Rp 4.000.000 per bulan"),
        ],
    },
    {
        "code": "C2",
        "name": "Jumlah Tanggungan",
        "criterion_type": "BENEFIT",
        "weight": Decimal("0.25"),
        "order": 2,
        "subcriteria": [
            (1, "Tidak ada tanggungan", "Tidak memiliki anggota keluarga yang ditanggung"),
            (2, "1-2 orang tanggungan", "Menanggung 1 hingga 2 anggota keluarga"),
            (3, "3-4 orang tanggungan", "Menanggung 3 hingga 4 anggota keluarga"),
            (4, "5-6 orang tanggungan", "Menanggung 5 hingga 6 anggota keluarga"),
            (5, ">= 7 orang tanggungan", "Menanggung 7 atau lebih anggota keluarga"),
        ],
    },
    {
        "code": "C3",
        "name": "Kondisi Tempat Tinggal",
        "criterion_type": "COST",
        "weight": Decimal("0.25"),
        "order": 3,
        "subcriteria": [
            (1, "Tidak Layak (Darurat / tanpa fasilitas dasar)", "Gubuk atau bangunan darurat tanpa fasilitas dasar"),
            (2, "Kurang Layak (Non-permanen, fasilitas minim)", "Rumah non-permanen dengan fasilitas sangat minim"),
            (3, "Cukup (Semi-permanen, fasilitas terbatas)", "Rumah semi-permanen dengan fasilitas terbatas"),
            (4, "Layak (Semi-permanen, fasilitas memadai)", "Rumah semi-permanen dengan fasilitas cukup memadai"),
            (5, "Sangat Layak (Permanen, fasilitas lengkap)", "Rumah permanen dengan fasilitas MCK lengkap dan air bersih"),
        ],
    },
    {
        "code": "C4",
        "name": "Kepemilikan Aset",
        "criterion_type": "COST",
        "weight": Decimal("0.20"),
        "order": 4,
        "subcriteria": [
            (1, "Tidak memiliki aset produktif apapun", "Tidak punya tanah, kendaraan, atau aset produktif"),
            (2, "Memiliki aset sederhana (sepeda/perabot dasar)", "Hanya memiliki perabot rumah dasar atau sepeda"),
            (3, "Memiliki aset menengah (motor/elektronik)", "Memiliki sepeda motor atau peralatan elektronik dasar"),
            (4, "Memiliki aset cukup besar (tanah/rumah sendiri)", "Memiliki tanah atau rumah sendiri"),
            (5, "Memiliki aset besar (mobil/usaha/properti)", "Memiliki kendaraan roda empat, usaha, atau properti lain"),
        ],
    },
]

# ---------------------------------------------------------------------------
# Demo staff accounts (development only)
# ---------------------------------------------------------------------------

DEMO_STAFF = [
    {
        "username": "kasi_kesos",
        "full_name": "Budi Hartono, S.Sos (Kasi Kesos)",
        "role": "SUPER_ADMIN",
        "password": "BansosAdmin2026!",
        "rt_number": "",
    },
    {
        "username": "ketua_rt003",
        "full_name": "Ketua RT 003",
        "role": "SURVEYOR",
        "password": "SurveyRT003!",
        "rt_number": "003",
    },
    {
        "username": "ketua_rt005",
        "full_name": "Ketua RT 005",
        "role": "SURVEYOR",
        "password": "SurveyRT005!",
        "rt_number": "005",
    },
    {
        "username": "lurah_jurangmangu",
        "full_name": "H. Ahmad Syarif (Lurah)",
        "role": "VIEWER",
        "password": "LurahViewer2026!",
        "rt_number": "",
    },
]


class Command(BaseCommand):
    help = "Seed initial criteria (C1-C4), subcriteria (Crips 1-5), demo staff accounts, and initial period/batch."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-criteria",
            action="store_true",
            help="Delete and recreate all criteria (dangerous in production).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        self._seed_criteria(reset=options.get("reset_criteria", False))
        self._seed_staff()
        batch = self._seed_period_and_batch()
        self._log_seed(batch=batch)

        self.stdout.write(self.style.SUCCESS("[OK] seed_initial_data completed successfully."))

    def _seed_criteria(self, reset: bool = False) -> None:
        if reset:
            Criteria.objects.all().delete()
            self.stdout.write("  ! All criteria deleted (--reset-criteria).")

        for cdata in CRITERIA_DATA:
            subcriteria_list = cdata.pop("subcriteria")
            criteria_obj, created = Criteria.objects.update_or_create(
                code=cdata["code"],
                defaults=cdata,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} {criteria_obj}")

            for crips_value, label, description in subcriteria_list:
                sc, sc_created = SubCriteria.objects.update_or_create(
                    criteria=criteria_obj,
                    crips_value=crips_value,
                    defaults={"label": label, "description": description},
                )
                if sc_created and self.verbosity >= 2:
                    self.stdout.write(f"    + SubCriteria {sc}")

            # Restore subcriteria key for idempotency
            cdata["subcriteria"] = subcriteria_list

    def _seed_staff(self) -> None:
        for sdata in DEMO_STAFF:
            password = sdata.pop("password")
            user, created = StaffUser.objects.get_or_create(
                username=sdata["username"],
                defaults=sdata,
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(f"  Created staff: {user}")
            else:
                self.stdout.write(f"  Exists  staff: {user}")
            sdata["password"] = password  # restore for idempotency

    def _seed_period_and_batch(self) -> SelectionBatch:
        admin_user = StaffUser.objects.filter(role=StaffUser.Role.SUPER_ADMIN).first()
        period, _ = Period.objects.get_or_create(
            name="Bansos Sembako Tahap I 2026",
            defaults={
                "year": 2026,
                "semester": 1,
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 6, 30),
                "is_active": True,
            },
        )
        batch, _ = SelectionBatch.objects.get_or_create(
            period=period,
            name="Seleksi Bansos Sembako Tahap I 2026",
            defaults={
                "quota": 30,
                "status": SelectionBatch.Status.COLLECTING,
                "created_by": admin_user,
            },
        )
        return batch

    def _log_seed(self, batch: SelectionBatch | None = None) -> None:
        AuditLog.objects.create(
            batch=batch,
            action=AuditLog.Action.SEED_DATA,
            performed_by="system:seed_initial_data",
            detail="Criteria C1–C4, SubCriteria Crips 1–5, demo staff, and initial batch seeded.",
        )

