"""
backend/core/serializers.py — DRF Serializers for Sistem Bansos SAW+XAI.

Provides serializers for:
  - Staff Authentication (Login & Profile)
  - Criteria & SubCriteria (including batch weight updates)
  - Period & SelectionBatch
  - Citizen & Evaluation input (with zero-plaintext NIK encryption)
  - Selection Results & Ranking views
  - Public Portal verification
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.crypto import validate_nik
from core.models import (
    Citizen,
    Criteria,
    Evaluation,
    EvaluationDetail,
    Period,
    SelectionBatch,
    SelectionResult,
    StaffUser,
    SubCriteria,
)
from core.permissions import check_surveyor_rt_scope, normalize_rt


class StaffUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffUser
        fields = ["id", "username", "full_name", "role", "rt_number", "created_at"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class SubCriteriaSerializer(serializers.ModelSerializer):
    score = serializers.IntegerField(source="crips_value", read_only=True)
    name = serializers.CharField(source="label", read_only=True)

    class Meta:
        model = SubCriteria
        fields = ["id", "crips_value", "score", "label", "name", "description"]


class CriteriaSerializer(serializers.ModelSerializer):
    subcriteria = SubCriteriaSerializer(many=True, read_only=True)
    attribute_type = serializers.CharField(source="criterion_type", read_only=True)

    class Meta:
        model = Criteria
        fields = ["id", "code", "name", "criterion_type", "attribute_type", "weight", "order", "subcriteria"]


class CriteriaItemUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    weight = serializers.DecimalField(
        max_digits=5,
        decimal_places=4,
        required=True,
        min_value=Decimal("0.0001"),
        max_value=Decimal("1.0000"),
    )
    attribute_type = serializers.CharField(required=False, default="")
    criterion_type = serializers.CharField(required=False, default="")


class CriteriaBatchUpdateSerializer(serializers.Serializer):
    criteria = CriteriaItemUpdateSerializer(many=True, required=True)

    def validate_criteria(self, value):
        if not value:
            raise serializers.ValidationError("Daftar kriteria tidak boleh kosong.")
        total_weight = sum(Decimal(str(item["weight"])) for item in value)
        if total_weight != Decimal("1.00"):
            raise serializers.ValidationError(
                f"Validasi gagal: Total bobot harus persis bernilai 1.00 (Total saat ini: {total_weight:.2f})"
            )
        return value


class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = ["id", "name", "year", "semester", "start_date", "end_date", "is_active"]


class SelectionBatchSerializer(serializers.ModelSerializer):
    batch_number = serializers.IntegerField(required=False)
    period_id = serializers.PrimaryKeyRelatedField(
        queryset=Period.objects.all(), source="period", write_only=True
    )
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = SelectionBatch
        fields = [
            "id",
            "name",
            "batch_number",
            "period",
            "period_id",
            "period_name",
            "quota",
            "status",
            "cutoff_score",
            "created_at",
        ]
        read_only_fields = ["id", "period", "status", "cutoff_score", "created_at"]

    def create(self, validated_data):
        batch_num = validated_data.pop("batch_number", None) or self.initial_data.get("batch_number")
        if batch_num and not validated_data.get("name"):
            validated_data["name"] = f"Batch {batch_num}"
        return super().create(validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["batch_number"] = instance.batch_number
        return ret


class CitizenCreateSerializer(serializers.Serializer):
    batch_id = serializers.IntegerField(required=True)
    nik = serializers.CharField(max_length=16, min_length=16, required=True)
    kk_last4 = serializers.CharField(max_length=4, min_length=4, required=True)
    full_name = serializers.CharField(max_length=200, required=True)
    address = serializers.CharField(required=False, default="Jurangmangu Barat")
    rt = serializers.CharField(max_length=10, required=True)
    rw = serializers.CharField(max_length=10, required=False, default="001")
    real_dependents_count = serializers.IntegerField(required=False, default=0)
    eligibility_status = serializers.ChoiceField(
        choices=["ELIGIBLE", "DISQUALIFIED"], required=False, default="ELIGIBLE"
    )
    tms_reason = serializers.CharField(required=False, allow_blank=True, default="")
    criteria_values = serializers.DictField(
        child=serializers.IntegerField(min_value=1, max_value=5), required=False, default=dict
    )

    def validate_nik(self, value):
        try:
            return validate_nik(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(str(exc))

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        target_rt = attrs.get("rt", "")

        if user and not check_surveyor_rt_scope(user, target_rt):
            raise serializers.ValidationError(
                {"error": f"Surveyor RT {user.rt_number} hanya berwenang mengelola data wilayah RT {user.rt_number}."}
            )

        try:
            attrs["batch"] = SelectionBatch.objects.get(id=attrs["batch_id"])
        except SelectionBatch.DoesNotExist:
            raise serializers.ValidationError({"batch_id": "Batch seleksi tidak ditemukan."})

        return attrs


class EvaluationDetailSerializer(serializers.ModelSerializer):
    criteria_code = serializers.CharField(source="criteria.code", read_only=True)
    criteria_name = serializers.CharField(source="criteria.name", read_only=True)

    class Meta:
        model = EvaluationDetail
        fields = ["id", "criteria_code", "criteria_name", "crips_value", "normalized_value"]


class SelectionResultItemSerializer(serializers.ModelSerializer):
    nik_masked = serializers.CharField(source="evaluation.citizen.nik_masked", read_only=True)
    name_masked = serializers.CharField(source="evaluation.citizen.full_name_masked", read_only=True)
    rt = serializers.CharField(source="evaluation.citizen.rt", read_only=True)
    rw = serializers.CharField(source="evaluation.citizen.rw", read_only=True)
    eligibility_status = serializers.CharField(source="evaluation.eligibility_status", read_only=True)
    tms_reason = serializers.CharField(source="evaluation.tms_reason", read_only=True)
    real_dependents_count = serializers.IntegerField(source="evaluation.real_dependents_count", read_only=True)
    details = EvaluationDetailSerializer(source="evaluation.details", many=True, read_only=True)

    class Meta:
        model = SelectionResult
        fields = [
            "id",
            "ranking",
            "status",
            "final_score_v",
            "tie_break_level",
            "explanation_source",
            "ai_narrative",
            "ai_payload_response",
            "nik_masked",
            "name_masked",
            "rt",
            "rw",
            "eligibility_status",
            "tms_reason",
            "real_dependents_count",
            "details",
        ]


class PublicCheckStatusRequestSerializer(serializers.Serializer):
    nik = serializers.CharField(max_length=16, min_length=16, required=True)
    kk_last4 = serializers.CharField(max_length=4, min_length=4, required=True)
    captcha_token = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_nik(self, value):
        try:
            return validate_nik(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(str(exc))
