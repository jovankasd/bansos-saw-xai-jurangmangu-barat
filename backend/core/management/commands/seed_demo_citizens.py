"""
backend/core/management/commands/seed_demo_citizens.py

Seeds realistic demo citizens and evaluations for Batch 1.
Includes 1 DISQUALIFIED (TMS) and 7 ELIGIBLE citizens with diverse Crips scores.
"""

from __future__ import annotations
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Citizen, Criteria, Evaluation, EvaluationDetail, SelectionBatch

DEMO_CITIZENS = [
    {
        "raw_nik": "3674031201900001",
        "kk_last4": "1111",
        "name": "Siti Rahmawati",
        "rt": "003",
        "rw": "001",
        "address": "Jl. Ceger Raya No. 12, RT 003/001",
        "eligibility": "DISQUALIFIED",
        "tms_reason": "ASN / Anggota TNI / Polri Aktif",
        "real_dependents": 3,
        "crips": {"C1": 2, "C2": 3, "C3": 2, "C4": 2},
    },
    {
        "raw_nik": "3674031505850002",
        "kk_last4": "2222",
        "name": "Ahmad Subagyo",
        "rt": "003",
        "rw": "001",
        "address": "Jl. Masjid Al-Barokah No. 5, RT 003/001",
        "eligibility": "ELIGIBLE",
        "tms_reason": "",
        "real_dependents": 5,
        "crips": {"C1": 1, "C2": 4, "C3": 1, "C4": 1},
    },
    {
        "raw_nik": "3674032007780003",
        "kk_last4": "3333",
        "name": "Budi Santoso",
        "rt": "003",
        "rw": "001",
        "address": "Gang Melati II No. 8, RT 003/001",
        "eligibility": "ELIGIBLE",
        "tms_reason": "",
        "real_dependents": 4,
        "crips": {"C1": 1, "C2": 3, "C3": 2, "C4": 1},
    },
    {
        "raw_nik": "3674031003820004",
        "kk_last4": "4444",
        "name": "Dewi Lestari",
        "rt": "005",
        "rw": "002",
        "address": "Jl. Jurangmangu Barat No. 44, RT 005/002",
        "eligibility": "ELIGIBLE",
        "tms_reason": "",
        "real_dependents": 3,
        "crips": {"C1": 2, "C2": 3, "C3": 2, "C4": 2},
    },
    {
        "raw_nik": "3674030509910005",
        "kk_last4": "5555",
        "name": "Eko Prasetyo",
        "rt": "005",
        "rw": "002",
        "address": "Jl. Garuda Mas Blok B3, RT 005/002",
        "eligibility": "ELIGIBLE",
        "tms_reason": "",
        "real_dependents": 2,
        "crips": {"C1": 2, "C2": 2, "C3": 3, "C4": 2},
    },
    {
        "raw_nik": "3674032512800006",
        "kk_last4": "6666",
        "name": "Farida Haryati",
        "rt": "003",
        "rw": "001",
        "address": "Jl. Ceger Permai No. 19, RT 003/001",
        "eligibility": "ELIGIBLE",
        "tms_reason": "",
        "real_dependents": 2,
        "crips": {"C1": 3, "C2": 2, "C3": 3, "C4": 3},
    },
    {
        "raw_nik": "3674031404750007",
        "kk_last4": "7777",
        "name": "Gunawan Wibowo",
        "rt": "003",
        "rw": "001",
        "address": "Gang Kenanga No. 2, RT 003/001",
        "eligibility": "ELIGIBLE",
        "tms_reason": "",
        "real_dependents": 1,
        "crips": {"C1": 4, "C2": 2, "C3": 4, "C4": 3},
    },
    {
        "raw_nik": "3674031808880008",
        "kk_last4": "8888",
        "name": "Hendra Wijaya",
        "rt": "005",
        "rw": "002",
        "address": "Jl. Raya Jurangmangu No. 71, RT 005/002",
        "eligibility": "ELIGIBLE",
        "tms_reason": "",
        "real_dependents": 1,
        "crips": {"C1": 4, "C2": 1, "C3": 4, "C4": 4},
    },
]


class Command(BaseCommand):
    help = "Seed demo citizens and evaluations for Batch 1."

    @transaction.atomic
    def handle(self, *args, **options):
        batch = SelectionBatch.objects.first()
        if not batch:
            self.stdout.write(self.style.ERROR("No SelectionBatch found. Run seed_initial_data first."))
            return

        batch.quota = 3
        batch.save()

        criteria_map = {c.code: c for c in Criteria.objects.all()}

        created_cnt = 0
        for item in DEMO_CITIZENS:
            citizen, _ = Citizen.objects.create_or_update_with_nik(
                raw_nik=item["raw_nik"],
                kk_last4=item["kk_last4"],
                full_name=item["name"],
                address=item["address"],
                rt=item["rt"],
                rw=item["rw"],
            )

            eval_obj, _ = Evaluation.objects.update_or_create(
                batch=batch,
                citizen=citizen,
                defaults={
                    "eligibility_status": item["eligibility"],
                    "tms_reason": item["tms_reason"],
                    "real_dependents_count": item["real_dependents"],
                    "is_rt_submitted": True,
                },
            )

            for c_code, crips_val in item["crips"].items():
                if c_code in criteria_map:
                    EvaluationDetail.objects.update_or_create(
                        evaluation=eval_obj,
                        criteria=criteria_map[c_code],
                        defaults={"raw_crips_value": crips_val},
                    )

            created_cnt += 1

        self.stdout.write(self.style.SUCCESS(f"[OK] Seeded {created_cnt} demo citizens and evaluations for batch '{batch.name}' (quota={batch.quota})."))
