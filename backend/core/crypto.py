"""
core/crypto.py — Cryptographic service layer (UU PDP No. 27/2022).

Provides:
  - AES-256-GCM at-rest encryption for NIK (enforces exactly 32-byte key)
  - HMAC-SHA256 deterministic indexing for nik_hash (with server-side pepper)
  - mask_nik()  -> "367403******0002"
  - mask_name() -> "Ahmad S******" (multi-word) | "Su*****" (single-word)
  - validate_nik() -> raises ValidationError for non-16-digit or non-numeric NIK
  - sign_pdf_download_token() / verify_pdf_download_token() via Django TimestampSigner
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import re

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

# ---------------------------------------------------------------------------
# Key material — loaded at module import time with dynamic @override_settings
# support while preserving monkeypatch compatibility on _AES_KEY / _HMAC_PEPPER.
# ---------------------------------------------------------------------------
_DEFAULT_AES_KEY: bytes = settings.NIK_AES_KEY_BYTES
_AES_KEY: bytes = _DEFAULT_AES_KEY

_DEFAULT_HMAC_PEPPER: str = settings.NIK_HMAC_PEPPER
_HMAC_PEPPER: str = _DEFAULT_HMAC_PEPPER

_NIK_PATTERN = re.compile(r"^[0-9]{16}$", re.ASCII)
_NIK_SUBSTRING_PATTERN = re.compile(r"(?<![0-9a-fA-F])[0-9]{16}(?![0-9a-fA-F])", re.ASCII)

# 12-byte GCM nonce + 16-byte NIK plaintext + 16-byte GCM tag = 44 bytes (60 base64url chars)
_GCM_BLOB_LEN = 12 + 16 + 16
_B64URL_GCM_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{59}=$", re.ASCII)
_PDF_SIGNER_SALT = "bansos.pdf_download"


def _resolve_aes_key() -> bytes:
    """Resolve the active 32-byte AES-256-GCM key, honoring monkeypatch and @override_settings."""
    if _AES_KEY is not _DEFAULT_AES_KEY:
        key = _AES_KEY
    else:
        settings_bytes = getattr(settings, "NIK_AES_KEY_BYTES", _DEFAULT_AES_KEY)
        if settings_bytes is not _DEFAULT_AES_KEY:
            key = settings_bytes
        else:
            raw_override = getattr(settings, "NIK_AES_KEY", None)
            if raw_override is not None:
                from config.security import parse_aes_256_key
                key = parse_aes_256_key(raw_override)
            else:
                key = _AES_KEY

    if not isinstance(key, (bytes, bytearray)) or len(key) != 32:
        actual_len = len(key) if isinstance(key, (bytes, bytearray)) else 0
        raise ValueError(
            f"NIK_AES_KEY wajib tepat 32 byte untuk AES-256-GCM, "
            f"tetapi ditemukan {actual_len} byte."
        )
    return bytes(key)


def _resolve_hmac_pepper() -> str:
    """Resolve the active HMAC-SHA256 pepper, honoring monkeypatch and @override_settings."""
    if _HMAC_PEPPER is not _DEFAULT_HMAC_PEPPER:
        pepper = _HMAC_PEPPER
    else:
        pepper = getattr(settings, "NIK_HMAC_PEPPER", _DEFAULT_HMAC_PEPPER)
    if not isinstance(pepper, str) or not pepper.strip():
        raise ValueError("NIK_HMAC_PEPPER tidak boleh kosong.")
    return pepper


# ---------------------------------------------------------------------------
# NIK validation
# ---------------------------------------------------------------------------

def validate_nik(nik: str) -> str:
    """
    Validate that *nik* is a string of exactly 16 ASCII numeric digits (0-9).

    Returns the validated NIK string.
    Raises django.core.exceptions.ValidationError otherwise.
    """
    if not isinstance(nik, str) or not _NIK_PATTERN.match(nik):
        raise ValidationError(
            "NIK harus terdiri dari tepat 16 digit angka.",
            code="invalid_nik",
        )
    return nik


def contains_plaintext_nik(value: str) -> bool:
    """Return True if *value* contains any 16-digit ASCII NIK (excluding 64-char hex hashes)."""
    if not isinstance(value, str):
        return False
    return bool(_NIK_SUBSTRING_PATTERN.search(value))


# ---------------------------------------------------------------------------
# AES-256-GCM encryption / decryption
# ---------------------------------------------------------------------------

def encrypt_nik(nik: str) -> str:
    """
    Encrypt *nik* using AES-256-GCM.

    Enforces that the key is exactly 32 bytes (raises ValueError otherwise).

    Returns a canonical base64url-encoded string: nonce (12 bytes) + ciphertext + tag.
    The raw NIK never appears in the returned value.
    """
    aes_key = _resolve_aes_key()
    validate_nik(nik)

    nonce = os.urandom(12)  # 96-bit nonce — recommended for GCM
    aesgcm = AESGCM(aes_key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, nik.encode("utf-8"), None)

    blob = nonce + ciphertext_with_tag
    return base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt_nik(token: str) -> str:
    """
    Decrypt an AES-256-GCM-encrypted NIK token produced by encrypt_nik().

    Returns the original plaintext NIK string.
    Raises ValueError if the token is malformed, non-canonical, or authentication fails.
    """
    aes_key = _resolve_aes_key()
    if not isinstance(token, str) or not _B64URL_GCM_TOKEN_PATTERN.match(token):
        raise ValueError("Gagal mendekripsi NIK: format base64url token tidak valid atau telah dimodifikasi.")

    try:
        blob = base64.urlsafe_b64decode(token.encode("ascii"))
    except (binascii.Error, UnicodeError, ValueError) as exc:
        raise ValueError("Gagal mendekripsi NIK: format base64 token tidak valid.") from exc

    if len(blob) != _GCM_BLOB_LEN or base64.urlsafe_b64encode(blob).decode("ascii") != token:
        raise ValueError("Gagal mendekripsi NIK: panjang atau kanonikalisasi token tidak memenuhi standar AES-256-GCM.")

    nonce = blob[:12]
    ciphertext_with_tag = blob[12:]

    aesgcm = AESGCM(aes_key)
    try:
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        plaintext = plaintext_bytes.decode("utf-8")
    except (InvalidTag, UnicodeError, ValueError) as exc:
        raise ValueError(
            "Gagal mendekripsi NIK: autentikasi GCM gagal atau ciphertext telah dimodifikasi."
        ) from exc

    if not _NIK_PATTERN.match(plaintext):
        raise ValueError("Gagal mendekripsi NIK: hasil dekripsi bukan 16 digit NIK yang valid.")
    return plaintext


# ---------------------------------------------------------------------------
# HMAC-SHA256 indexing (deterministic, server-side pepper)
# ---------------------------------------------------------------------------

def hash_nik(nik: str) -> str:
    """
    Produce a deterministic 64-character hex HMAC-SHA256 digest of *nik*
    using the server-side pepper (NIK_HMAC_PEPPER).

    Validates that *nik* is a valid 16-digit ASCII NIK before hashing.
    Used for fast, privacy-preserving lookups (nik_hash column) without
    storing plaintext NIK.
    """
    validate_nik(nik)
    pepper = _resolve_hmac_pepper()
    digest = hmac.new(
        pepper.encode("utf-8"),
        nik.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest  # 64 hex characters


# ---------------------------------------------------------------------------
# Masking helpers (visual — for UI display, never persisted as plaintext NIK)
# ---------------------------------------------------------------------------

def mask_nik(nik: str) -> str:
    """
    Mask a 16-digit NIK to the PRD-specified display format.

    Example: "3674031208850002" -> "367403******0002"
    """
    validate_nik(nik)
    return nik[:6] + "******" + nik[-4:]


def mask_name(full_name: str) -> str:
    """
    Mask a person's name per the PRD privacy spec:

    - Multi-word names: first word shown in full, subsequent words have first
      character shown + asterisks for remaining characters.
      "Ahmad Subarjo"  -> "Ahmad S******"
      "Budi Su"        -> "Budi S*"
    - Single-word names: first two characters shown + asterisks (or masked if <= 2 chars).
      "Sukarno"        -> "Su*****"
      "Su"             -> "S*"
      "A"              -> "*"
    """
    if not isinstance(full_name, str):
        return ""
    parts = full_name.strip().split()
    if not parts:
        return ""
    if len(parts) == 1:
        word = parts[0]
        if len(word) == 1:
            return "*"
        if len(word) == 2:
            return word[0] + "*"
        return word[:2] + "*" * (len(word) - 2)

    # Multi-word: keep first word, mask remaining words (first char + stars)
    masked_parts = [parts[0]]
    for word in parts[1:]:
        if not word:
            continue
        if len(word) == 1:
            masked_parts.append("*")
        else:
            masked_parts.append(word[0] + "*" * (len(word) - 1))
    return " ".join(masked_parts)


# ---------------------------------------------------------------------------
# Signed PDF download tokens (Django TimestampSigner)
# ---------------------------------------------------------------------------

def sign_pdf_download_token(evaluation_id: int) -> str:
    """
    Produce a tamper-proof, time-limited signed token encoding *evaluation_id*.

    Uses Django's TimestampSigner so the token carries an embedded timestamp
    that can be checked for expiry without storing state.
    """
    if isinstance(evaluation_id, bool) or not isinstance(evaluation_id, int) or evaluation_id <= 0:
        raise ValueError("evaluation_id harus berupa bilangan bulat positif.")
    signer = TimestampSigner(salt=_PDF_SIGNER_SALT)
    return signer.sign(str(evaluation_id))


def verify_pdf_download_token(token: str, max_age: int = 900) -> int:
    """
    Verify and decode a PDF download token produced by sign_pdf_download_token().

    Returns the original evaluation_id as an int.
    Raises django.core.signing.SignatureExpired or BadSignature on failure.
    *max_age* defaults to 900 seconds (15 minutes) per PRD §FR-06.
    """
    if not isinstance(token, str) or not token.strip():
        raise BadSignature("Token unduhan PDF kosong atau tidak valid.")
    signer = TimestampSigner(salt=_PDF_SIGNER_SALT)
    if max_age is not None and max_age <= 0:
        # First verify signature integrity, then enforce immediate expiration
        signer.unsign(token)
        raise SignatureExpired("Token unduhan PDF telah kedaluwarsa.")
    unsigned = signer.unsign(token, max_age=max_age)
    if not unsigned.isascii() or not unsigned.isdigit() or int(unsigned) <= 0:
        raise BadSignature("Payload token unduhan PDF bukan bilangan bulat positif.")
    return int(unsigned)


