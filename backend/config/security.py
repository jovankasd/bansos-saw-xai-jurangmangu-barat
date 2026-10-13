"""
Security, Secret Management, and Auth Guardrail Validators.

Implements fail-closed startup validation and log sanitization in accordance with:
- UU PDP No. 27 Tahun 2022 (AES-256-GCM 32-byte key + HMAC-SHA256 pepper separation)
- OWASP Top 10 (A01 Broken Access Control, A02 Cryptographic Failures, A05 Security Misconfiguration, A07 Auth Failures)
- OWASP Top 10 for LLM Applications (LLM02 Sensitive Information Disclosure)
"""

from __future__ import annotations

import base64
import binascii
import logging
import re
from typing import Iterable

from django.core.exceptions import ImproperlyConfigured

# Placeholders or weak values that MUST be rejected when DEBUG=False
FORBIDDEN_PLACEHOLDER_PREFIXES = (
    "change_me",
    "your-secret",
    "your_secret",
    "placeholder",
    "secret",
    "password",
    "default",
    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
)

# Regex patterns for redacting PII (16-digit NIK) and Bearer tokens from server logs
# Uses negative hex lookbehind/lookahead so 'nik_3674031208850002' is redacted while 64-char hex hashes are preserved.
NIK_LOG_REGEX = re.compile(r"(?<![0-9a-fA-F])\d{16}(?![0-9a-fA-F])", re.ASCII)
BEARER_TOKEN_REGEX = re.compile(r"(Bearer\s+)[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", re.IGNORECASE)
_B64_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_\-+/]+={0,2}$", re.ASCII)


def parse_aes_256_key(raw_key: str) -> bytes:
    """
    Parse and strictly validate a 32-byte (256-bit) key for AES-256-GCM.
    Supports:
    - 64-character hexadecimal string -> 32 bytes
    - 32-byte UTF-8 string -> 32 bytes
    - Base64-encoded 32-byte key -> 32 bytes
    Raises ValueError if the resolved key is not strictly 32 bytes.
    """
    if not raw_key or not isinstance(raw_key, str):
        raise ValueError("NIK_AES_KEY wajib diisi dan harus menghasilkan tepat 32 byte untuk AES-256-GCM.")

    cleaned = raw_key.strip()

    # 1. Check if 64-char hex string (32 bytes)
    if len(cleaned) == 64:
        try:
            key_bytes = binascii.unhexlify(cleaned)
            if len(key_bytes) == 32:
                return key_bytes
        except (binascii.Error, ValueError):
            pass

    # 2. Check raw UTF-8 byte length == 32
    utf8_bytes = cleaned.encode("utf-8")
    if len(utf8_bytes) == 32:
        return utf8_bytes

    # 3. Check base64 encoded 32-byte key (strictly valid base64 chars)
    if len(cleaned) in (43, 44) and _B64_KEY_PATTERN.match(cleaned):
        try:
            padded = cleaned + "=" * (-len(cleaned) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
            if len(decoded) == 32:
                return decoded
        except (binascii.Error, ValueError):
            pass

    raise ValueError(
        f"NIK_AES_KEY tidak valid: panjang kunci terdeteksi {len(utf8_bytes)} byte UTF-8. "
        "Standar AES-256-GCM (UU PDP) mewajibkan kunci tepat 32 byte (atau 64 karakter hex)."
    )


def validate_secret_management(
    *,
    debug: bool,
    django_secret_key: str,
    nik_aes_key: str,
    nik_hmac_pepper: str,
    cors_allowed_origins: Iterable[str],
    allowed_hosts: Iterable[str],
) -> bytes:
    """
    Fail-closed validator for application secrets and origin boundaries.
    Returns the validated 32-byte AES-256 key.
    Raises ValueError or ImproperlyConfigured if any security constraint is violated.
    """
    # 1. Always enforce 32-byte AES-256 key regardless of DEBUG mode
    aes_key_bytes = parse_aes_256_key(nik_aes_key)

    # 2. Always enforce minimum length for HMAC-SHA256 pepper
    if not nik_hmac_pepper or len(nik_hmac_pepper.strip().encode("utf-8")) < 32:
        raise ValueError(
            "NIK_HMAC_PEPPER wajib memiliki panjang minimal 32 byte untuk keamanan indeks HMAC-SHA256."
        )

    # 3. Enforce cryptographic key separation (AES key != HMAC pepper != Django SECRET_KEY)
    normalized_aes = nik_aes_key.strip()
    normalized_pepper = nik_hmac_pepper.strip()
    normalized_django_secret = (django_secret_key or "").strip()

    if normalized_aes == normalized_pepper or aes_key_bytes == normalized_pepper.encode("utf-8"):
        raise ValueError(
            "Pelanggaran Key Separation: NIK_AES_KEY dan NIK_HMAC_PEPPER dilarang menggunakan nilai yang sama."
        )

    if normalized_django_secret and (
        normalized_django_secret == normalized_aes or normalized_django_secret == normalized_pepper
    ):
        raise ValueError(
            "Pelanggaran Key Separation: DJANGO_SECRET_KEY dilarang sama dengan NIK_AES_KEY atau NIK_HMAC_PEPPER."
        )

    # 4. Never allow wildcard '*' in CORS_ALLOWED_ORIGINS
    origins_list = [o.strip() for o in cors_allowed_origins if o and o.strip()]
    if "*" in origins_list or any("*" in origin for origin in origins_list):
        raise ImproperlyConfigured(
            "Pelanggaran CORS Guardrail: Wildcard ('*') dilarang pada CORS_ALLOWED_ORIGINS."
        )

    # 5. Strict production checks when DEBUG is False
    if not debug:
        if not normalized_django_secret or len(normalized_django_secret) < 50:
            raise ImproperlyConfigured(
                "Pada mode produksi (DJANGO_DEBUG=False), DJANGO_SECRET_KEY wajib minimal 50 karakter."
            )

        for secret_name, secret_val in (
            ("DJANGO_SECRET_KEY", normalized_django_secret),
            ("NIK_AES_KEY", normalized_aes),
            ("NIK_HMAC_PEPPER", normalized_pepper),
        ):
            lower_val = secret_val.lower()
            if any(lower_val.startswith(prefix) for prefix in FORBIDDEN_PLACEHOLDER_PREFIXES):
                raise ImproperlyConfigured(
                    f"Pada mode produksi (DJANGO_DEBUG=False), {secret_name} masih menggunakan nilai contoh/placeholder."
                )

        hosts_list = [h.strip() for h in allowed_hosts if h and h.strip()]
        if not hosts_list or "*" in hosts_list:
            raise ImproperlyConfigured(
                "Pada mode produksi (DJANGO_DEBUG=False), DJANGO_ALLOWED_HOSTS wajib ditentukan secara eksplisit tanpa '*'."
            )

    return aes_key_bytes


def validate_auth_guardrails(rest_framework_config: dict, simple_jwt_config: dict) -> None:
    """
    Validates that authentication and authorization guardrails remain fail-closed:
    - Default DRF permission MUST require authentication (IsAuthenticated), never AllowAny globally.
    - JWT access token lifetime MUST be bounded (<= 60 minutes).
    - Refresh token rotation MUST be enabled.
    """
    default_perms = rest_framework_config.get("DEFAULT_PERMISSION_CLASSES", [])
    if not default_perms or "rest_framework.permissions.AllowAny" in default_perms:
        raise ImproperlyConfigured(
            "Auth Guardrail Gagal: DEFAULT_PERMISSION_CLASSES tidak boleh AllowAny secara global (harus fail-closed)."
        )
    if "rest_framework.permissions.IsAuthenticated" not in default_perms:
        raise ImproperlyConfigured(
            "Auth Guardrail Gagal: 'rest_framework.permissions.IsAuthenticated' wajib menjadi permission default."
        )

    default_auth = rest_framework_config.get("DEFAULT_AUTHENTICATION_CLASSES", [])
    if "rest_framework_simplejwt.authentication.JWTAuthentication" not in default_auth:
        raise ImproperlyConfigured(
            "Auth Guardrail Gagal: JWTAuthentication wajib aktif pada DEFAULT_AUTHENTICATION_CLASSES."
        )

    access_lifetime = simple_jwt_config.get("ACCESS_TOKEN_LIFETIME")
    if access_lifetime is None or access_lifetime.total_seconds() > 3600:
        raise ImproperlyConfigured(
            "Auth Guardrail Gagal: ACCESS_TOKEN_LIFETIME tidak boleh melebihi 60 menit."
        )

    if not simple_jwt_config.get("ROTATE_REFRESH_TOKENS", False):
        raise ImproperlyConfigured(
            "Auth Guardrail Gagal: ROTATE_REFRESH_TOKENS wajib bernilai True."
        )


def scrub_sensitive_text(text: str) -> str:
    """Redacts 16-digit NIK numbers and JWT Bearer tokens from any log string."""
    if not isinstance(text, str):
        return text
    scrubbed = NIK_LOG_REGEX.sub("[REDACTED_NIK_16]", text)
    scrubbed = BEARER_TOKEN_REGEX.sub(r"\1[REDACTED_JWT]", scrubbed)
    return scrubbed


class ZeroPiiLogFilter(logging.Filter):
    """
    Logging filter that prevents accidental leakage of 16-digit plaintext NIKs
    or JWT Bearer tokens into application logs (UU PDP No. 27/2022 compliance).
    Formats and scrubs the full message so Exception/int/dict args cannot bypass redaction.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
            record.msg = scrub_sensitive_text(rendered)
            record.args = ()
        except Exception:
            if isinstance(record.msg, str):
                record.msg = scrub_sensitive_text(record.msg)
        if getattr(record, "exc_text", None) and isinstance(record.exc_text, str):
            record.exc_text = scrub_sensitive_text(record.exc_text)
        return True

