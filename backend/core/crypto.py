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
# Key material — loaded once at module import time.
# settings.NIK_AES_KEY_BYTES is already validated as exactly 32 bytes by
# config.security.validate_secret_management() at Django startup.
# ---------------------------------------------------------------------------
_AES_KEY: bytes = settings.NIK_AES_KEY_BYTES
_HMAC_PEPPER: str = settings.NIK_HMAC_PEPPER

_NIK_PATTERN = re.compile(r"^[0-9]{16}$", re.ASCII)
_NIK_SUBSTRING_PATTERN = re.compile(r"[0-9]{16}", re.ASCII)

# 12-byte GCM nonce + 16-byte NIK plaintext + 16-byte GCM tag = 44 bytes
_MIN_GCM_BLOB_LEN = 12 + 16 + 16


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
    """Return True if *value* contains any 16-digit contiguous ASCII number."""
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

    Returns a base64url-encoded string: nonce (12 bytes) + ciphertext + tag.
    The raw NIK never appears in the returned value.
    """
    if len(_AES_KEY) != 32:
        raise ValueError(
            f"NIK_AES_KEY wajib tepat 32 byte untuk AES-256-GCM, "
            f"tetapi ditemukan {len(_AES_KEY)} byte."
        )
    validate_nik(nik)

    nonce = os.urandom(12)  # 96-bit nonce — recommended for GCM
    aesgcm = AESGCM(_AES_KEY)
    ciphertext_with_tag = aesgcm.encrypt(nonce, nik.encode("utf-8"), None)

    blob = nonce + ciphertext_with_tag
    return base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt_nik(token: str) -> str:
    """
    Decrypt an AES-256-GCM-encrypted NIK token produced by encrypt_nik().

    Returns the original plaintext NIK string.
    Raises ValueError if the token is malformed or authentication fails.
    """
    if len(_AES_KEY) != 32:
        raise ValueError(
            f"NIK_AES_KEY wajib tepat 32 byte untuk AES-256-GCM, "
            f"tetapi ditemukan {len(_AES_KEY)} byte."
        )
    if not isinstance(token, str) or not token.strip():
        raise ValueError("Gagal mendekripsi NIK: token kosong atau bukan string.")

    try:
        blob = base64.urlsafe_b64decode(token.encode("ascii"))
    except (binascii.Error, UnicodeError, ValueError) as exc:
        raise ValueError("Gagal mendekripsi NIK: format base64 token tidak valid.") from exc

    if len(blob) < _MIN_GCM_BLOB_LEN:
        raise ValueError("Gagal mendekripsi NIK: panjang token tidak memenuhi standar AES-256-GCM.")

    nonce = blob[:12]
    ciphertext_with_tag = blob[12:]

    aesgcm = AESGCM(_AES_KEY)
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
    digest = hmac.new(
        _HMAC_PEPPER.encode("utf-8"),
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

_PDF_SIGNER = TimestampSigner(salt="bansos.pdf_download")


def sign_pdf_download_token(evaluation_id: int) -> str:
    """
    Produce a tamper-proof, time-limited signed token encoding *evaluation_id*.

    Uses Django's TimestampSigner so the token carries an embedded timestamp
    that can be checked for expiry without storing state.
    """
    if isinstance(evaluation_id, bool) or not isinstance(evaluation_id, int) or evaluation_id <= 0:
        raise ValueError("evaluation_id harus berupa bilangan bulat positif.")
    return _PDF_SIGNER.sign(str(evaluation_id))


def verify_pdf_download_token(token: str, max_age: int = 900) -> int:
    """
    Verify and decode a PDF download token produced by sign_pdf_download_token().

    Returns the original evaluation_id as an int.
    Raises django.core.signing.SignatureExpired or BadSignature on failure.
    *max_age* defaults to 900 seconds (15 minutes) per PRD §FR-06.
    """
    if not isinstance(token, str) or not token.strip():
        raise BadSignature("Token unduhan PDF kosong atau tidak valid.")
    if max_age is not None and max_age <= 0:
        # First verify signature integrity, then enforce immediate expiration
        _PDF_SIGNER.unsign(token)
        raise SignatureExpired("Token unduhan PDF telah kedaluwarsa.")
    unsigned = _PDF_SIGNER.unsign(token, max_age=max_age)
    return int(unsigned)

