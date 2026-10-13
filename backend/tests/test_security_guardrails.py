"""
Unit tests for Security, Secret Management, and Authentication Guardrails.
Verifies compliance with `/security-and-hardening` and UU PDP No. 27/2022.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config.security import (
    ZeroPiiLogFilter,
    parse_aes_256_key,
    validate_auth_guardrails,
    validate_secret_management,
)


def test_env_example_files_exist_and_contain_required_placeholders():
    backend_env = Path(settings.BASE_DIR) / ".env.example"
    root_env = Path(settings.BASE_DIR).parent / ".env.example"
    frontend_env = Path(settings.BASE_DIR).parent / "frontend" / ".env.example"

    assert backend_env.exists(), "backend/.env.example wajib tersedia"
    assert root_env.exists(), "root .env.example wajib tersedia"
    assert frontend_env.exists(), "frontend/.env.example wajib tersedia"

    backend_text = backend_env.read_text(encoding="utf-8")
    for required_key in (
        "DJANGO_DEBUG=False",
        "DJANGO_SECRET_KEY=",
        "NIK_AES_KEY=",
        "NIK_HMAC_PEPPER=",
        "CORS_ALLOWED_ORIGINS=",
        "GEMINI_API_KEY=",
        "TURNSTILE_SECRET_KEY=",
    ):
        assert required_key in backend_text

    # Frontend .env.example must NEVER expose backend cryptographic keys
    frontend_text = frontend_env.read_text(encoding="utf-8")
    assert "NIK_AES_KEY=" not in frontend_text
    assert "NIK_HMAC_PEPPER=" not in frontend_text


def test_parse_aes_256_key_strictly_enforces_32_bytes():
    # Valid 64-char hex -> 32 bytes
    hex_key = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    assert len(parse_aes_256_key(hex_key)) == 32

    # Valid 32-char UTF-8 string -> 32 bytes
    utf8_key = "12345678901234567890123456789012"
    assert len(parse_aes_256_key(utf8_key)) == 32

    # Reject 16-byte (AES-128) or 24-byte (AES-192) keys
    with pytest.raises(ValueError, match="tepat 32 byte"):
        parse_aes_256_key("1234567890123456")

    with pytest.raises(ValueError, match="tepat 32 byte"):
        parse_aes_256_key("")


def test_secret_management_enforces_key_separation_and_blocks_wildcard_cors():
    valid_aes = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    valid_pepper = "pepper-jurangmangu-barat-hmac-sha256-unique-secret-key-2026"
    valid_django = "django-high-entropy-secret-key-for-testing-purpose-only-9876543210"

    # Key separation failure: AES key == HMAC pepper
    with pytest.raises(ValueError, match="Key Separation"):
        validate_secret_management(
            debug=True,
            django_secret_key=valid_django,
            nik_aes_key=valid_aes,
            nik_hmac_pepper=valid_aes,
            cors_allowed_origins=["http://localhost:5173"],
            allowed_hosts=["localhost"],
        )

    # Wildcard CORS failure
    with pytest.raises(ImproperlyConfigured, match="Wildcard"):
        validate_secret_management(
            debug=True,
            django_secret_key=valid_django,
            nik_aes_key=valid_aes,
            nik_hmac_pepper=valid_pepper,
            cors_allowed_origins=["*"],
            allowed_hosts=["localhost"],
        )

    # Production mode (debug=False) rejects template placeholder keys
    with pytest.raises(ImproperlyConfigured, match="placeholder"):
        validate_secret_management(
            debug=False,
            django_secret_key="CHANGE_ME_GENERATE_A_50_PLUS_CHAR_HIGH_ENTROPY_DJANGO_SECRET_KEY",
            nik_aes_key=valid_aes,
            nik_hmac_pepper=valid_pepper,
            cors_allowed_origins=["https://bansos.jurangmangubarat.go.id"],
            allowed_hosts=["bansos.jurangmangubarat.go.id"],
        )


def test_auth_guardrails_reject_allow_any_and_unbounded_jwt():
    # Active settings must pass fail-closed auth guardrails
    validate_auth_guardrails(settings.REST_FRAMEWORK, settings.SIMPLE_JWT)
    assert settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"

    # Reject global AllowAny permission
    with pytest.raises(ImproperlyConfigured, match="AllowAny"):
        validate_auth_guardrails(
            {
                "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
                "DEFAULT_AUTHENTICATION_CLASSES": [
                    "rest_framework_simplejwt.authentication.JWTAuthentication"
                ],
            },
            settings.SIMPLE_JWT,
        )

    # Reject excessive JWT access token lifetime (> 60m)
    with pytest.raises(ImproperlyConfigured, match="ACCESS_TOKEN_LIFETIME"):
        validate_auth_guardrails(
            settings.REST_FRAMEWORK,
            {
                **settings.SIMPLE_JWT,
                "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
            },
        )


def test_zero_pii_log_filter_redacts_16_digit_nik_and_bearer_jwt():
    log_filter = ZeroPiiLogFilter()
    record = logging.LogRecord(
        name="bansos.audit",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Verifikasi gagal untuk NIK 3674031208850002 dengan header Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoxfQ.sig123",
        args=(),
        exc_info=None,
    )
    assert log_filter.filter(record) is True
    assert "3674031208850002" not in record.msg
    assert "[REDACTED_NIK_16]" in record.msg
    assert "eyJhbGciOiJIUzI1NiJ9" not in record.msg
    assert "Bearer [REDACTED_JWT]" in record.msg

    # Also redact when NIK is inside an Exception arg or prefixed with 'nik_'
    exc_record = logging.LogRecord(
        name="bansos.audit",
        level=logging.ERROR,
        pathname=__file__,
        lineno=20,
        msg="Exception during lookup for key=nik_3674031208850002: %s",
        args=(ValueError("Failed on NIK 3674031208859999"),),
        exc_info=None,
    )
    assert log_filter.filter(exc_record) is True
    rendered = exc_record.getMessage()
    assert "3674031208850002" not in rendered
    assert "3674031208859999" not in rendered
    assert rendered.count("[REDACTED_NIK_16]") == 2

