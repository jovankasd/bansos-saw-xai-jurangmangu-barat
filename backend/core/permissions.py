"""
backend/core/permissions.py — RBAC Permission Guards for Sistem Bansos SAW+XAI.

Roles defined in PRD Section 3 & AGENTS.md:
  1. SUPER_ADMIN (Kasi Kesos):
     - Full read/write on criteria, batches, citizen import, calculation, publish, audit logs.
  2. SURVEYOR (Ketua RT):
     - Ingest / manage citizen data ONLY for their designated RT (request.user.rt_number).
     - Submit RT data (mark-rt-submitted).
     - View results scoped to their RT.
     - CANNOT alter criteria, create batches, calculate SAW, approve, or publish.
  3. VIEWER (Lurah):
     - Read-only across all batches, criteria, calculation results, XAI progress, and metrics.
     - Exclusive authorization to approve batches in 'Narrated' status.
     - CANNOT alter criteria, create batches, calculate SAW, or publish.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission
from core.models import StaffUser


class IsSuperAdmin(BasePermission):
    """Allows access only to authenticated Super Admin (Kasi Kesos)."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == StaffUser.Role.SUPER_ADMIN
        )


class IsSurveyor(BasePermission):
    """Allows access only to authenticated Surveyor (Ketua RT)."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == StaffUser.Role.SURVEYOR
        )


class IsViewer(BasePermission):
    """Allows access only to authenticated Viewer (Lurah)."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == StaffUser.Role.VIEWER
        )


class IsSuperAdminOrViewer(BasePermission):
    """Allows access to Super Admin or Viewer (Lurah)."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None)
            in (StaffUser.Role.SUPER_ADMIN, StaffUser.Role.VIEWER)
        )


class IsSuperAdminOrSurveyor(BasePermission):
    """Allows access to Super Admin or Surveyor (Ketua RT)."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None)
            in (StaffUser.Role.SUPER_ADMIN, StaffUser.Role.SURVEYOR)
        )


class IsStaff(BasePermission):
    """Allows access to any valid staff member (Super Admin, Surveyor, Viewer)."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None)
            in (
                StaffUser.Role.SUPER_ADMIN,
                StaffUser.Role.SURVEYOR,
                StaffUser.Role.VIEWER,
            )
        )


def normalize_rt(rt: str | int | None) -> str:
    """Normalize RT string to 3 digits (e.g. '3' -> '003')."""
    if rt is None:
        return ""
    clean = str(rt).strip()
    return clean.zfill(3) if clean.isdigit() else clean


def check_surveyor_rt_scope(user: StaffUser, target_rt: str | int | None) -> bool:
    """
    Returns True if user has authority to manage target_rt.
    Super Admin has authority over all RTs.
    Surveyor only has authority if target_rt matches user.rt_number.
    """
    if not user or not user.is_authenticated:
        return False
    if user.role == StaffUser.Role.SUPER_ADMIN:
        return True
    if user.role == StaffUser.Role.SURVEYOR:
        user_rt = normalize_rt(user.rt_number)
        norm_target = normalize_rt(target_rt)
        return bool(user_rt and user_rt == norm_target)
    return False
