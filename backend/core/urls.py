"""
backend/core/urls.py — Route definitions for Sistem Bansos SAW+XAI.
"""

from __future__ import annotations

from django.urls import path
from core.views import (
    BatchListView,
    CitizenCreateView,
    CitizenImportExcelView,
    CriteriaBatchUpdateView,
    CriteriaListView,
    PublicCheckStatusView,
    SelectionApproveView,
    SelectionCalculateView,
    SelectionExportExcelView,
    SelectionGenerateXaiView,
    SelectionMarkRtSubmittedView,
    SelectionPublishView,
    SelectionResultsView,
    SelectionXaiProgressView,
    StaffLoginView,
)

urlpatterns = [
    # Auth
    path("auth/login/", StaffLoginView.as_view(), name="auth-login"),

    # Criteria Management
    path("criteria/", CriteriaListView.as_view(), name="criteria-list"),
    path("criteria/batch-update/", CriteriaBatchUpdateView.as_view(), name="criteria-batch-update"),

    # Batches
    path("batches/", BatchListView.as_view(), name="batch-list-create"),

    # Citizens & Excel Ingest
    path("citizens/", CitizenCreateView.as_view(), name="citizen-create"),
    path("citizens/import-excel/", CitizenImportExcelView.as_view(), name="citizens-import-excel"),

    # Selection Workflow & RBAC
    path("selection/<int:batch_id>/mark-rt-submitted/", SelectionMarkRtSubmittedView.as_view(), name="selection-mark-rt-submitted"),
    path("selection/<int:batch_id>/calculate/", SelectionCalculateView.as_view(), name="selection-calculate"),
    path("selection/<int:batch_id>/results/", SelectionResultsView.as_view(), name="selection-results"),
    path("selection/<int:batch_id>/generate-xai/", SelectionGenerateXaiView.as_view(), name="selection-generate-xai"),
    path("selection/<int:batch_id>/xai-progress/", SelectionXaiProgressView.as_view(), name="selection-xai-progress"),
    path("selection/<int:batch_id>/approve/", SelectionApproveView.as_view(), name="selection-approve"),
    path("selection/<int:batch_id>/publish/", SelectionPublishView.as_view(), name="selection-publish"),
    path("selection/<int:batch_id>/export-excel/", SelectionExportExcelView.as_view(), name="selection-export-excel"),

    # Public Citizen Portal
    path("public/check-status/", PublicCheckStatusView.as_view(), name="public-check-status"),
]
