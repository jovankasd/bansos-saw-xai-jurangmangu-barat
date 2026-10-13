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

import re
from decimal import Decimal

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.crypto import (
    contains_plaintext_nik,
    decrypt_nik,
    encrypt_nik,
    hash_nik,
    mask_name,
    mask_nik,
    validate_nik,
)

_KK_LAST4_PATTERN = re.compile(r"^[0-9]{4}$", re.ASCII)
_NIK_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_NIK_MASKED_PATTERN = re.compile(r"^[0-9]{6}\*{6}[0-9]{4}$", re.ASCII)


# ---------------------------------------------------------------------------
# Generic QuerySet & Model Mixin for PRD Section 9 Field Aliases
# ---------------------------------------------------------------------------

class AliasQuerySet(models.QuerySet):
    """
    Translates PRD Section 9 field aliases (e.g., attribute_type, condition_label,
    period_name, disqualification_reason, normalized_score, user_action) across all
    QuerySet operations (.filter, .exclude, .get, .create, .get_or_create,
    .update_or_create, .update, .order_by).
    """

    FIELD_ALIASES: dict[str, str] = {}
    NULL_TO_EMPTY_FIELDS: set[str] = set()

    def _map_kwargs(self, kwargs: dict) -> dict:
        if not kwargs:
            return kwargs
        mapped = {}
        for key, val in kwargs.items():
            parts = key.split("__", 1)
            root = parts[0]
            if root in self.FIELD_ALIASES:
                canonical = self.FIELD_ALIASES[root]
                key = f"{canonical}__{parts[1]}" if len(parts) > 1 else canonical
                root = canonical
            if root in self.NULL_TO_EMPTY_FIELDS and val is None and len(parts) == 1:
                val = ""
            mapped[key] = val
        return mapped

    def _map_fields(self, fields: tuple[str, ...]) -> tuple[str, ...]:
        if not self.FIELD_ALIASES or not fields:
            return fields
        out = []
        for f in fields:
            prefix = "-" if f.startswith("-") else ""
            raw = f[1:] if prefix else f
            parts = raw.split("__", 1)
            root = parts[0]
            if root in self.FIELD_ALIASES:
                canonical = self.FIELD_ALIASES[root]
                raw = f"{canonical}__{parts[1]}" if len(parts) > 1 else canonical
            out.append(f"{prefix}{raw}")
        return tuple(out)

    def filter(self, *args, **kwargs):
        return super().filter(*args, **self._map_kwargs(kwargs))

    def exclude(self, *args, **kwargs):
        return super().exclude(*args, **self._map_kwargs(kwargs))

    def get(self, *args, **kwargs):
        return super().get(*args, **self._map_kwargs(kwargs))

    def create(self, **kwargs):
        return super().create(**self._map_kwargs(kwargs))

    def get_or_create(self, defaults=None, **kwargs):
        mapped_defaults = self._map_kwargs(defaults) if defaults else defaults
        return super().get_or_create(defaults=mapped_defaults, **self._map_kwargs(kwargs))

    def update_or_create(self, defaults=None, create_defaults=None, **kwargs):
        mapped_defaults = self._map_kwargs(defaults) if defaults else defaults
        mapped_create = self._map_kwargs(create_defaults) if create_defaults else create_defaults
        return super().update_or_create(
            defaults=mapped_defaults,
            create_defaults=mapped_create,
            **self._map_kwargs(kwargs),
        )

    def update(self, **kwargs):
        return super().update(**self._map_kwargs(kwargs))

    def order_by(self, *field_names):
        return super().order_by(*self._map_fields(field_names))


def _remap_update_fields(update_fields, aliases: dict[str, str]):
    if update_fields is None or not aliases:
        return update_fields
    return [aliases.get(f, f) for f in update_fields]


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

class CriteriaQuerySet(AliasQuerySet):
    FIELD_ALIASES = {"attribute_type": "criterion_type"}


class Criteria(models.Model):
    _FIELD_ALIASES = {"attribute_type": "criterion_type"}

    class CriterionType(models.TextChoices):
        BENEFIT = "BENEFIT", "Benefit (semakin tinggi semakin baik)"
        COST = "COST", "Cost (semakin rendah semakin baik)"

    code = models.CharField(max_length=10, unique=True)   # C1, C2, C3, C4
    name = models.CharField(max_length=200)
    criterion_type = models.CharField(max_length=10, choices=CriterionType.choices)
    weight = models.DecimalField(max_digits=5, decimal_places=4)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    objects = CriteriaQuerySet.as_manager()

    class Meta:
        db_table = "criteria"
        ordering = ["order"]
        verbose_name_plural = "Criteria"

    def __init__(self, *args, **kwargs):
        if "attribute_type" in kwargs and "criterion_type" not in kwargs:
            kwargs["criterion_type"] = kwargs.pop("attribute_type")
        super().__init__(*args, **kwargs)

    @property
    def attribute_type(self) -> str:
        return self.criterion_type

    @attribute_type.setter
    def attribute_type(self, value: str) -> None:
        self.criterion_type = value

    def save(self, *args, **kwargs) -> None:
        if "update_fields" in kwargs:
            kwargs["update_fields"] = _remap_update_fields(kwargs["update_fields"], self._FIELD_ALIASES)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code} - {self.name} ({self.criterion_type}, w={self.weight})"


class SubCriteriaQuerySet(AliasQuerySet):
    FIELD_ALIASES = {"condition_label": "label"}


class SubCriteria(models.Model):
    """Crips 1..5 per criterion — maps a numeric raw value to a label."""
    _FIELD_ALIASES = {"condition_label": "label"}

    criteria = models.ForeignKey(Criteria, on_delete=models.CASCADE, related_name="subcriteria")
    crips_value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )   # 1..5
    label = models.CharField(max_length=300)
    description = models.TextField(blank=True)

    objects = SubCriteriaQuerySet.as_manager()

    class Meta:
        db_table = "subcriteria"
        constraints = [
            models.UniqueConstraint(
                fields=["criteria", "crips_value"],
                name="uq_subcriteria_criteria_value",
            ),
        ]
        ordering = ["criteria__order", "crips_value"]

    def __init__(self, *args, **kwargs):
        if "condition_label" in kwargs and "label" not in kwargs:
            kwargs["label"] = kwargs.pop("condition_label")
        super().__init__(*args, **kwargs)

    @property
    def condition_label(self) -> str:
        return self.label

    @condition_label.setter
    def condition_label(self, value: str) -> None:
        self.label = value

    def clean(self) -> None:
        super().clean()
        if isinstance(self.crips_value, bool) or not isinstance(self.crips_value, int) or not (1 <= self.crips_value <= 5):
            raise ValidationError("crips_value wajib bernilai antara 1 hingga 5.")

    def save(self, *args, **kwargs) -> None:
        if "update_fields" in kwargs:
            kwargs["update_fields"] = _remap_update_fields(kwargs["update_fields"], self._FIELD_ALIASES)
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.criteria.code} - Crips {self.crips_value}: {self.label}"


# ---------------------------------------------------------------------------
# Period & SelectionBatch
# ---------------------------------------------------------------------------

class PeriodQuerySet(AliasQuerySet):
    FIELD_ALIASES = {"period_name": "name"}


class Period(models.Model):
    _FIELD_ALIASES = {"period_name": "name"}

    name = models.CharField(max_length=200, unique=True)   # e.g. "Semester I 2026"
    year = models.PositiveSmallIntegerField(default=2026)
    semester = models.PositiveSmallIntegerField(
        choices=[(1, "Semester I"), (2, "Semester II")],
        default=1,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PeriodQuerySet.as_manager()

    class Meta:
        db_table = "period"
        ordering = ["-year", "-semester"]

    def __init__(self, *args, **kwargs):
        if "period_name" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs.pop("period_name")
        super().__init__(*args, **kwargs)

    @property
    def period_name(self) -> str:
        return self.name

    @period_name.setter
    def period_name(self, value: str) -> None:
        self.name = value

    def save(self, *args, **kwargs) -> None:
        if "update_fields" in kwargs:
            kwargs["update_fields"] = _remap_update_fields(kwargs["update_fields"], self._FIELD_ALIASES)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


def _coerce_approved_by(value) -> str:
    if value is None:
        return ""
    if isinstance(value, StaffUser):
        return value.full_name or value.username
    return str(value)


class SelectionBatchQuerySet(AliasQuerySet):
    def _map_kwargs(self, kwargs: dict) -> dict:
        mapped = super()._map_kwargs(kwargs)
        if "approved_by" in mapped:
            mapped["approved_by"] = _coerce_approved_by(mapped["approved_by"])
        return mapped


class SelectionBatch(models.Model):
    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        COLLECTING = "Collecting", "Collecting"
        CALCULATED = "Calculated", "Calculated"
        NARRATED = "Narrated", "Narrated"
        APPROVED = "Approved", "Approved"
        PUBLISHED = "Published", "Published"

    period = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="batches")
    name = models.CharField(max_length=200, blank=True, default="")
    quota = models.PositiveSmallIntegerField()
    cutoff_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        StaffUser,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_batches",
    )
    approved_by = models.CharField(max_length=200, blank=True, default="")
    calculated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SelectionBatchQuerySet.as_manager()

    class Meta:
        db_table = "selection_batch"
        ordering = ["-created_at"]

    def __setattr__(self, name: str, value) -> None:
        if name == "approved_by":
            value = _coerce_approved_by(value)
        super().__setattr__(name, value)

    def __str__(self) -> str:
        return f"{self.name or self.period.name} [{self.status}]"


# ---------------------------------------------------------------------------
# BatchCriteria — immutable snapshot of criteria weights per batch
# ---------------------------------------------------------------------------

class BatchCriteriaQuerySet(AliasQuerySet):
    FIELD_ALIASES = {"attribute_type": "criterion_type"}


class BatchCriteria(models.Model):
    """
    Frozen snapshot of Criteria metadata at calculation time.

    NEVER modified after creation; all post-calc modules read frozen_weight,
    never master Criteria.weight.
    """
    _FIELD_ALIASES = {"attribute_type": "criterion_type"}

    batch = models.ForeignKey(SelectionBatch, on_delete=models.CASCADE, related_name="batch_criteria")
    criteria = models.ForeignKey(Criteria, on_delete=models.PROTECT, related_name="batch_snapshots")
    code = models.CharField(max_length=10)          # denormalised for speed
    name = models.CharField(max_length=200)
    criterion_type = models.CharField(max_length=10)
    frozen_weight = models.DecimalField(max_digits=5, decimal_places=4)
    frozen_at = models.DateTimeField(auto_now_add=True)

    objects = BatchCriteriaQuerySet.as_manager()

    class Meta:
        db_table = "batch_criteria"
        constraints = [
            models.UniqueConstraint(fields=["batch", "criteria"], name="uq_batch_criteria"),
        ]
        ordering = ["criteria__order"]

    def __init__(self, *args, **kwargs):
        if "attribute_type" in kwargs and "criterion_type" not in kwargs:
            kwargs["criterion_type"] = kwargs.pop("attribute_type")
        super().__init__(*args, **kwargs)

    @property
    def attribute_type(self) -> str:
        return self.criterion_type

    @attribute_type.setter
    def attribute_type(self, value: str) -> None:
        self.criterion_type = value

    def save(self, *args, **kwargs) -> None:
        if "update_fields" in kwargs:
            kwargs["update_fields"] = _remap_update_fields(kwargs["update_fields"], self._FIELD_ALIASES)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"[{self.batch}] {self.code} frozen_weight={self.frozen_weight}"


# ---------------------------------------------------------------------------
# Citizen — PII-hardened (NIK encrypted at rest, never plaintext)
# ---------------------------------------------------------------------------

class CitizenQuerySet(models.QuerySet):
    """Enforces UU PDP No. 27/2022 at-rest validation even on bulk_create() and update()."""

    def bulk_create(self, objs, *args, **kwargs):
        objs_list = list(objs)
        for obj in objs_list:
            if obj.full_name:
                obj.full_name_masked = mask_name(obj.full_name)
            obj.clean()
        return super().bulk_create(objs_list, *args, **kwargs)

    def update(self, **kwargs):
        for field_name in ("nik_encrypted", "nik_masked", "nik_hash"):
            if field_name in kwargs and contains_plaintext_nik(str(kwargs[field_name])):
                raise ValidationError(
                    f"Pelanggaran UU PDP No. 27/2022: NIK plaintext 16 digit dilarang disimpan pada {field_name}."
                )
        if "nik_hash" in kwargs:
            val = kwargs["nik_hash"]
            if not isinstance(val, str) or not _NIK_HASH_PATTERN.match(val):
                raise ValidationError("Pelanggaran UU PDP No. 27/2022: nik_hash wajib berupa 64 karakter hex HMAC-SHA256.")
        if "nik_masked" in kwargs:
            val = kwargs["nik_masked"]
            if not isinstance(val, str) or not _NIK_MASKED_PATTERN.match(val):
                raise ValidationError("Pelanggaran UU PDP No. 27/2022: nik_masked wajib berformat 367403******0002.")
        if "nik_encrypted" in kwargs:
            try:
                decrypt_nik(kwargs["nik_encrypted"])
            except ValueError as exc:
                raise ValidationError(
                    "Pelanggaran UU PDP No. 27/2022: nik_encrypted wajib berupa ciphertext AES-256-GCM yang valid."
                ) from exc
        if "kk_last4" in kwargs:
            val = kwargs["kk_last4"]
            if not isinstance(val, str) or not _KK_LAST4_PATTERN.match(val):
                raise ValidationError("kk_last4 wajib terdiri dari tepat 4 digit angka.")
        if "full_name" in kwargs and "full_name_masked" not in kwargs:
            kwargs["full_name_masked"] = mask_name(kwargs["full_name"])
        return super().update(**kwargs)


class CitizenManager(models.Manager.from_queryset(CitizenQuerySet)):
    """Custom manager providing NIK-aware upsert and UU PDP bulk protection."""

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
        if not isinstance(kk_last4, str) or not _KK_LAST4_PATTERN.match(kk_last4):
            raise ValidationError(
                "kk_last4 wajib terdiri dari tepat 4 digit angka.",
                code="invalid_kk_last4",
            )

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
    full_name_masked = models.CharField(max_length=300, blank=True)

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

    def clean(self) -> None:
        super().clean()
        if (
            contains_plaintext_nik(self.nik_encrypted)
            or contains_plaintext_nik(self.nik_masked)
            or contains_plaintext_nik(self.nik_hash)
        ):
            raise ValidationError(
                "Pelanggaran UU PDP No. 27/2022: NIK plaintext 16 digit dilarang disimpan pada nik_encrypted, nik_masked, atau nik_hash."
            )
        if not isinstance(self.nik_hash, str) or not _NIK_HASH_PATTERN.match(self.nik_hash):
            raise ValidationError(
                "Pelanggaran UU PDP No. 27/2022: nik_hash wajib berupa 64 karakter hex HMAC-SHA256."
            )
        if not isinstance(self.nik_masked, str) or not _NIK_MASKED_PATTERN.match(self.nik_masked):
            raise ValidationError(
                "Pelanggaran UU PDP No. 27/2022: nik_masked wajib berformat 6 digit awal + ****** + 4 digit akhir."
            )
        try:
            decrypt_nik(self.nik_encrypted)
        except ValueError as exc:
            raise ValidationError(
                "Pelanggaran UU PDP No. 27/2022: nik_encrypted wajib berupa ciphertext AES-256-GCM yang valid."
            ) from exc
        if not isinstance(self.kk_last4, str) or not _KK_LAST4_PATTERN.match(self.kk_last4):
            raise ValidationError("kk_last4 wajib terdiri dari tepat 4 digit angka.")

    def save(self, *args, **kwargs) -> None:
        if self.full_name:
            self.full_name_masked = mask_name(self.full_name)
            if "update_fields" in kwargs and kwargs["update_fields"] is not None:
                uf = list(kwargs["update_fields"])
                if "full_name" in uf and "full_name_masked" not in uf:
                    uf.append("full_name_masked")
                    kwargs["update_fields"] = uf
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Citizen {self.nik_masked} ({self.full_name_masked})"

    def decrypt_nik(self) -> str:
        """Decrypt NIK — ONLY call from PDF generation with AuditLog entry."""
        return decrypt_nik(self.nik_encrypted)


# ---------------------------------------------------------------------------
# Evaluation — per-citizen per-batch assessment
# ---------------------------------------------------------------------------

class EvaluationQuerySet(AliasQuerySet):
    FIELD_ALIASES = {"disqualification_reason": "tms_reason"}
    NULL_TO_EMPTY_FIELDS = {"tms_reason"}


class Evaluation(models.Model):
    _FIELD_ALIASES = {"disqualification_reason": "tms_reason"}

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

    objects = EvaluationQuerySet.as_manager()

    class Meta:
        db_table = "evaluation"
        constraints = [
            models.UniqueConstraint(fields=["batch", "citizen"], name="uq_evaluation_batch_citizen"),
        ]
        ordering = ["created_at"]

    def __init__(self, *args, **kwargs):
        if "disqualification_reason" in kwargs and "tms_reason" not in kwargs:
            kwargs["tms_reason"] = kwargs.pop("disqualification_reason") or ""
        elif "tms_reason" in kwargs and kwargs["tms_reason"] is None:
            kwargs["tms_reason"] = ""
        super().__init__(*args, **kwargs)

    @property
    def disqualification_reason(self) -> str:
        return self.tms_reason

    @disqualification_reason.setter
    def disqualification_reason(self, value: str | None) -> None:
        self.tms_reason = value or ""

    def save(self, *args, **kwargs) -> None:
        if self.tms_reason is None:
            self.tms_reason = ""
        if "update_fields" in kwargs:
            kwargs["update_fields"] = _remap_update_fields(kwargs["update_fields"], self._FIELD_ALIASES)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Eval {self.citizen.nik_masked} @ {self.batch}"


# ---------------------------------------------------------------------------
# EvaluationDetail — per-criterion raw Crips value + normalized r_ij
# ---------------------------------------------------------------------------

class EvaluationDetailQuerySet(AliasQuerySet):
    FIELD_ALIASES = {"normalized_score": "normalized_value"}


class EvaluationDetail(models.Model):
    _FIELD_ALIASES = {"normalized_score": "normalized_value"}

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="details")
    criteria = models.ForeignKey(Criteria, on_delete=models.PROTECT)
    raw_crips_value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )   # 1..5
    normalized_value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.0000"),
    )

    objects = EvaluationDetailQuerySet.as_manager()

    class Meta:
        db_table = "evaluation_detail"
        constraints = [
            models.UniqueConstraint(
                fields=["evaluation", "criteria"],
                name="uq_evaluation_detail",
            ),
        ]
        ordering = ["criteria__order"]

    def __init__(self, *args, **kwargs):
        if "normalized_score" in kwargs and "normalized_value" not in kwargs:
            kwargs["normalized_value"] = kwargs.pop("normalized_score")
        super().__init__(*args, **kwargs)

    @property
    def normalized_score(self) -> Decimal:
        return self.normalized_value

    @normalized_score.setter
    def normalized_score(self, value: Decimal) -> None:
        self.normalized_value = value

    def save(self, *args, **kwargs) -> None:
        if "update_fields" in kwargs:
            kwargs["update_fields"] = _remap_update_fields(kwargs["update_fields"], self._FIELD_ALIASES)
        super().save(*args, **kwargs)

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
        GEMINI_API = "GEMINI_API", "Gemini Flash API (PRD Alias)"
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
# AuditLog — immutable audit trail (Zero-PII enforced)
# ---------------------------------------------------------------------------

class AuditLogQuerySet(AliasQuerySet):
    FIELD_ALIASES = {"user_action": "action"}


class AuditLog(models.Model):
    _FIELD_ALIASES = {"user_action": "action"}

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

    batch = models.ForeignKey(
        SelectionBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    performed_by = models.CharField(max_length=200)  # username or "system"
    target_object_repr = models.TextField(blank=True)  # str() of target — no PII
    detail = models.TextField(blank=True)              # additional context — no PII
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]

    def __init__(self, *args, **kwargs):
        if "user_action" in kwargs and "action" not in kwargs:
            kwargs["action"] = kwargs.pop("user_action")
        super().__init__(*args, **kwargs)

    @property
    def user_action(self) -> str:
        return self.action

    @user_action.setter
    def user_action(self, value: str) -> None:
        self.action = value

    def clean(self) -> None:
        super().clean()
        if (
            contains_plaintext_nik(self.detail)
            or contains_plaintext_nik(self.target_object_repr)
            or contains_plaintext_nik(self.performed_by)
        ):
            raise ValidationError(
                "Pelanggaran UU PDP No. 27/2022: AuditLog dilarang menyimpan NIK plaintext 16 digit."
            )

    def save(self, *args, **kwargs) -> None:
        if "update_fields" in kwargs:
            kwargs["update_fields"] = _remap_update_fields(kwargs["update_fields"], self._FIELD_ALIASES)
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} by {self.performed_by}"


