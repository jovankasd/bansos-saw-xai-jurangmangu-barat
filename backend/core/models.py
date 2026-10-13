"""
core/models.py — Database models for Sistem Bansos SAW+XAI.

Tables (9 PRD + StaffUser):
  StaffUser           — custom user with role (SUPER_ADMIN, SURVEYOR, VIEWER) and RT number
  Criteria            — master criteria table C1..C4
  SubCriteria         — Crips score definitions (1..5 per criterion)
  BatchCriteria       — immutable weight snapshot per batch (never mutated post-calculation)
  Citizen             — citizen record with NIK stored only as ciphertext + hash + mask
  Period              — period (semester/year) for selection
  SelectionBatch      — selection batch state machine (Draft->Published)
  Evaluation          — per-citizen per-batch evaluation (includes real_dependents_count)
  EvaluationDetail    — per-criterion raw value for one Evaluation
  SelectionResult     — SAW output: final_score_v, ranking, status, XAI narrative
  AuditLog            — immutable audit trail for every sensitive operation

Key constraints enforced:
  - Evaluation: UniqueConstraint(fields=["batch", "citizen"])
  - BatchCriteria: UniqueConstraint(fields=["batch", "criteria"])
  - EvaluationDetail: UniqueConstraint(fields=["evaluation", "criteria"])
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from core.crypto import (
    decrypt_nik,
    encrypt_nik,
    hash_nik,
    mask_name,
    mask_nik,
    validate_nik,
)


# ---------------------------------------------------------------------------
# StaffUser
# ---------------------------------------------------------------------------

class StaffUserManager(BaseUserManager):
    def create_user(self, username: str, password: str, role: str = "SURVEYOR", **extra):
        user = self.model(username=username, role=role, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, password: str, **extra):
        extra.setdefault("role", "SUPER_ADMIN")
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(username, password, **extra)


class StaffUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin (Kasi Kesos)"
        SURVEYOR = "SURVEYOR", "Surveyor (Ketua RT)"
        VIEWER = "VIEWER", "Viewer (Lurah)"

    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SURVEYOR)
    # RT number applicable only to SURVEYOR role (e.g. "003")
    rt_number = models.CharField(max_length=10, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    objects = StaffUserManager()

    class Meta:
        db_table = "staff_user"
        verbose_name = "Staff User"

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"


# ---------------------------------------------------------------------------
# Criteria & SubCriteria
# ---------------------------------------------------------------------------

class Criteria(models.Model):
    class CriterionType(models.TextChoices):
        BENEFIT = "BENEFIT", "Benefit (semakin tinggi semakin baik)"
        COST = "COST", "Cost (semakin rendah semakin baik)"

    code = models.CharField(max_length=10, unique=True)   # C1, C2, C3, C4
    name = models.CharField(max_length=200)
    criterion_type = models.CharField(max_length=10, choices=CriterionType.choices)
    weight = models.DecimalField(max_digits=5, decimal_places=4)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "criteria"
        ordering = ["order"]
        verbose_name_plural = "Criteria"

    def __str__(self) -> str:
        return f"{self.code} — {self.name} ({self.criterion_type}, w={self.weight})"


class SubCriteria(models.Model):
    """Crips 1..5 per criterion — maps a numeric raw value to a label."""
    criteria = models.ForeignKey(Criteria, on_delete=models.CASCADE, related_name="subcriteria")
    crips_value = models.PositiveSmallIntegerField()   # 1..5
    label = models.CharField(max_length=300)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "subcriteria"
        unique_together = [("criteria", "crips_value")]
        ordering = ["criteria__order", "crips_value"]

    def __str__(self) -> str:
        return f"{self.criteria.code} — Crips {self.crips_value}: {self.label}"


# ---------------------------------------------------------------------------
# Period & SelectionBatch
# ---------------------------------------------------------------------------

class Period(models.Model):
    name = models.CharField(max_length=200, unique=True)   # e.g. "Semester I 2026"
    year = models.PositiveSmallIntegerField()
    semester = models.PositiveSmallIntegerField(choices=[(1, "Semester I"), (2, "Semester II")])
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "period"
        ordering = ["-year", "-semester"]

    def __str__(self) -> str:
        return self.name


class SelectionBatch(models.Model):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        COLLECTING = "Collecting", "Collecting"
        CALCULATED = "Calculated", "Calculated"
        NARRATED = "Narrated", "Narrated"
        APPROVED = "Approved", "Approved"
        PUBLISHED = "Published", "Published"

    period = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="batches")
    name = models.CharField(max_length=200)
    quota = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        StaffUser, on_delete=models.PROTECT, related_name="created_batches"
    )
    approved_by = models.ForeignKey(
        StaffUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_batches",
    )
    calculated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "selection_batch"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} [{self.status}]"


# ---------------------------------------------------------------------------
# BatchCriteria — immutable snapshot of criteria weights per batch
# ---------------------------------------------------------------------------

class BatchCriteria(models.Model):
    """
    Frozen snapshot of Criteria metadata at calculation time.

    NEVER modified after creation; all post-calc modules read frozen_weight,
    never master Criteria.weight.
    """
    batch = models.ForeignKey(SelectionBatch, on_delete=models.CASCADE, related_name="batch_criteria")
    criteria = models.ForeignKey(Criteria, on_delete=models.PROTECT, related_name="batch_snapshots")
    code = models.CharField(max_length=10)          # denormalised for speed
    name = models.CharField(max_length=200)
    criterion_type = models.CharField(max_length=10)
    frozen_weight = models.DecimalField(max_digits=5, decimal_places=4)
    frozen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "batch_criteria"
        constraints = [
            models.UniqueConstraint(fields=["batch", "criteria"], name="uq_batch_criteria"),
        ]
        ordering = ["criteria__order"]

    def __str__(self) -> str:
        return f"[{self.batch}] {self.code} frozen_weight={self.frozen_weight}"


# ---------------------------------------------------------------------------
# Citizen — PII-hardened (NIK encrypted at rest, never plaintext)
# ---------------------------------------------------------------------------

class CitizenManager(models.Manager):
    """Custom manager providing NIK-aware upsert."""

    def create_or_update_with_nik(
        self,
        *,
        raw_nik: str,
        kk_last4: str,
        full_name: str,
        address: str,
        rt: str,
        rw: str,
        **extra_fields,
    ) -> tuple[Citizen, bool]:
        """
        Upsert a Citizen record keyed by nik_hash (HMAC-SHA256 of raw_nik).

        Returns (citizen, created) — same contract as get_or_create().
        The raw_nik is NEVER stored as plaintext; it is immediately encrypted
        via AES-256-GCM and stored as nik_encrypted.
        """
        validate_nik(raw_nik)

        nik_h = hash_nik(raw_nik)
        nik_enc = encrypt_nik(raw_nik)
        nik_mask = mask_nik(raw_nik)

        defaults = {
            "nik_encrypted": nik_enc,
            "nik_masked": nik_mask,
            "kk_last4": kk_last4,
            "full_name": full_name,
            "full_name_masked": mask_name(full_name),
            "address": address,
            "rt": rt,
            "rw": rw,
            **extra_fields,
        }
        obj, created = self.get_or_create(nik_hash=nik_h, defaults=defaults)
        if not created:
            # Update mutable fields on re-import
            for field, value in defaults.items():
                setattr(obj, field, value)
            obj.save(update_fields=list(defaults.keys()))
        return obj, created


class Citizen(models.Model):
    # --- Cryptographic NIK storage (UU PDP No. 27/2022) ---
    nik_hash = models.CharField(max_length=64, unique=True, db_index=True)
    nik_encrypted = models.TextField()           # base64(nonce + ciphertext + tag)
    nik_masked = models.CharField(max_length=20) # "367403******0002" — safe for display

    # --- Household ---
    kk_last4 = models.CharField(max_length=4)   # last 4 digits of KK for public portal auth
    full_name = models.CharField(max_length=300)
    full_name_masked = models.CharField(max_length=300)

    # --- Address ---
    address = models.TextField()
    rt = models.CharField(max_length=10)
    rw = models.CharField(max_length=10)

    # --- Administrative status ---
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CitizenManager()

    class Meta:
        db_table = "citizen"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Citizen {self.nik_masked} ({self.full_name_masked})"

    def decrypt_nik(self) -> str:
        """Decrypt NIK — ONLY call from PDF generation with AuditLog entry."""
        return decrypt_nik(self.nik_encrypted)


# ---------------------------------------------------------------------------
# Evaluation — per-citizen per-batch assessment
# ---------------------------------------------------------------------------

class Evaluation(models.Model):
    class EligibilityStatus(models.TextChoices):
        ELIGIBLE = "ELIGIBLE", "Eligible (Lolos Administratif)"
        DISQUALIFIED = "DISQUALIFIED", "Disqualified (TMS)"

    class TmsReason(models.TextChoices):
        ASN = "ASN", "ASN / TNI / Polri"
        PKH_GANDA = "PKH_GANDA", "Penerima PKH Ganda"
        PINDAH = "PINDAH", "Pindah Domisili"
        MENINGGAL = "MENINGGAL", "Meninggal Dunia"
        NONE = "", "Tidak TMS"

    batch = models.ForeignKey(SelectionBatch, on_delete=models.CASCADE, related_name="evaluations")
    citizen = models.ForeignKey(Citizen, on_delete=models.PROTECT, related_name="evaluations")

    eligibility_status = models.CharField(
        max_length=20,
        choices=EligibilityStatus.choices,
        default=EligibilityStatus.ELIGIBLE,
    )
    tms_reason = models.CharField(max_length=20, choices=TmsReason.choices, blank=True, default="")

    # Tie-breaker Level 3 (FR-03)
    real_dependents_count = models.PositiveSmallIntegerField(default=0)

    # Surveyor meta
    surveyor = models.ForeignKey(
        StaffUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_evaluations",
    )
    is_rt_submitted = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluation"
        constraints = [
            models.UniqueConstraint(fields=["batch", "citizen"], name="uq_evaluation_batch_citizen"),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Eval {self.citizen.nik_masked} @ {self.batch}"


# ---------------------------------------------------------------------------
# EvaluationDetail — per-criterion raw Crips value for one Evaluation
# ---------------------------------------------------------------------------

class EvaluationDetail(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="details")
    criteria = models.ForeignKey(Criteria, on_delete=models.PROTECT)
    raw_crips_value = models.PositiveSmallIntegerField()   # 1..5

    class Meta:
        db_table = "evaluation_detail"
        constraints = [
            models.UniqueConstraint(
                fields=["evaluation", "criteria"],
                name="uq_evaluation_detail",
            ),
        ]
        ordering = ["criteria__order"]

    def __str__(self) -> str:
        return f"{self.evaluation} — {self.criteria.code}={self.raw_crips_value}"


# ---------------------------------------------------------------------------
# SelectionResult — SAW output + XAI narrative
# ---------------------------------------------------------------------------

class SelectionResult(models.Model):
    class ResultStatus(models.TextChoices):
        LOLOS = "LOLOS", "Lolos"
        TIDAK_LOLOS = "TIDAK_LOLOS", "Tidak Lolos"
        DISKUALIFIKASI_TMS = "DISKUALIFIKASI_TMS", "Diskualifikasi TMS"

    class ExplanationSource(models.TextChoices):
        GEMINI = "GEMINI", "Gemini Flash API"
        DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK", "Deterministic Fallback"
        INELIGIBLE_NOTICE = "INELIGIBLE_NOTICE", "TMS Notice (No XAI)"

    evaluation = models.OneToOneField(Evaluation, on_delete=models.CASCADE, related_name="result")
    status = models.CharField(max_length=25, choices=ResultStatus.choices)
    final_score_v = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    ranking = models.PositiveIntegerField(null=True, blank=True)
    tie_break_level = models.PositiveSmallIntegerField(default=0)   # 0=no tie, 1..4=tier used
    cutoff_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    # XAI narrative fields
    ai_narrative = models.TextField(blank=True)
    ai_payload_response = models.JSONField(null=True, blank=True)
    explanation_source = models.CharField(
        max_length=30,
        choices=ExplanationSource.choices,
        blank=True,
        default="",
    )
    narrated_at = models.DateTimeField(null=True, blank=True)

    # Signed token for individual PDF download (public portal)
    download_token = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "selection_result"
        ordering = ["ranking"]

    def __str__(self) -> str:
        return f"{self.evaluation} -> {self.status} (rank={self.ranking}, V={self.final_score_v})"


# ---------------------------------------------------------------------------
# AuditLog — immutable audit trail
# ---------------------------------------------------------------------------

class AuditLog(models.Model):
    class Action(models.TextChoices):
        NIK_DECRYPT = "NIK_DECRYPT", "NIK Decryption (PDF Generation)"
        BATCH_CALCULATED = "BATCH_CALCULATED", "Batch SAW Calculated"
        BATCH_APPROVED = "BATCH_APPROVED", "Batch Approved"
        BATCH_PUBLISHED = "BATCH_PUBLISHED", "Batch Published"
        XAI_GENERATED = "XAI_GENERATED", "XAI Narrative Generated"
        CITIZEN_IMPORT = "CITIZEN_IMPORT", "Citizen Data Import (Excel)"
        PUBLIC_CHECK = "PUBLIC_CHECK", "Public Status Check"
        PDF_DOWNLOADED = "PDF_DOWNLOADED", "PDF Downloaded"
        SEED_DATA = "SEED_DATA", "Initial Seed Data"

    action = models.CharField(max_length=30, choices=Action.choices)
    performed_by = models.CharField(max_length=200)  # username or "system"
    target_object_repr = models.TextField(blank=True)  # str() of target — no PII
    detail = models.TextField(blank=True)              # additional context — no PII
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} by {self.performed_by}"
