"""
backend/core/services/rate_limiter.py — Anti-Bot & Public Portal Shield.

Enforces multi-tier defense per PRD §10.6 & FR-06:
  1. Turnstile CAPTCHA verification (Cloudflare Turnstile or test token).
     - Must be evaluated BEFORE incrementing NIK failure counter.
  2. IP Rate Limiting: 5 requests / minute / IP via Django Cache (HTTP 429).
  3. Per-NIK Lockout: 15-minute lockout after 5 consecutive failed attempts
     (wrong kk_last4) on the same NIK, persisting across rotating IPs (HTTP 429).
"""

from __future__ import annotations

import logging
from typing import Tuple
from django.conf import settings
from django.core.cache import cache

from core.crypto import hash_nik

logger = logging.getLogger(__name__)

IP_RATE_LIMIT_MAX = getattr(settings, "PUBLIC_PORTAL_RATE_LIMIT_PER_MIN", 5)
IP_RATE_LIMIT_WINDOW = 60  # seconds

NIK_LOCKOUT_MAX_FAILURES = getattr(settings, "PUBLIC_PORTAL_NIK_LOCKOUT_ATTEMPTS", 5)
NIK_LOCKOUT_DURATION = getattr(settings, "PUBLIC_PORTAL_NIK_LOCKOUT_SECONDS", 900)  # 15 minutes


def verify_turnstile_captcha(captcha_token: str | None, remote_ip: str = "") -> bool:
    """
    Validates Turnstile CAPTCHA response token.
    In testing or debug environments, accepts dummy/test tokens.
    """
    if not captcha_token or not captcha_token.strip():
        return False

    token = captcha_token.strip()

    # Reject known invalid test tokens
    if token in ("invalid_token", "fail", "expired"):
        return False

    # Accept test tokens strictly in DEBUG / test environments
    if settings.DEBUG and token in ("valid_test_token", "turnstile_dummy_token", "cf_turnstile_response_token_here"):
        return True

    # Cloudflare Turnstile production verification
    secret_key = getattr(settings, "TURNSTILE_SECRET_KEY", "")
    if not secret_key:
        if settings.DEBUG:
            logger.warning("TURNSTILE_SECRET_KEY is empty; allowing in DEBUG mode only.")
            return True
        logger.error("TURNSTILE_SECRET_KEY is empty in production mode. Rejecting verification (Fail-Closed).")
        return False

    try:
        import urllib.parse
        import urllib.request
        import json

        data = urllib.parse.urlencode({
            "secret": secret_key,
            "response": token,
            "remoteip": remote_ip,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=data,
            headers={"User-Agent": "Bansos-PublicPortal/1.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return bool(res_json.get("success", False))
    except Exception as exc:
        logger.error("Turnstile verification error: %s", exc)
        return False


def check_ip_rate_limit(remote_ip: str) -> Tuple[bool, str]:
    """
    Checks if remote_ip has exceeded 5 requests in the last 60 seconds.
    Returns (is_allowed, error_message).
    """
    if not remote_ip:
        return True, ""

    cache_key = f"portal_rate_ip_{remote_ip}"
    current_count = cache.get(cache_key)

    if current_count is not None and int(current_count) >= IP_RATE_LIMIT_MAX:
        return False, "Terlalu banyak permintaan dari IP Anda. Silakan coba beberapa saat lagi."

    if current_count is None:
        cache.set(cache_key, 1, timeout=IP_RATE_LIMIT_WINDOW)
    else:
        try:
            cache.incr(cache_key)
        except Exception:
            cache.set(cache_key, int(current_count) + 1, timeout=IP_RATE_LIMIT_WINDOW)

    return True, ""


def check_nik_lockout(nik: str) -> Tuple[bool, str]:
    """
    Checks if the given NIK is currently locked out due to 5 consecutive failures.
    Returns (is_allowed, error_message).
    """
    if not nik:
        return True, ""

    nik_digest = hash_nik(nik)
    lockout_key = f"portal_lockout_nik_{nik_digest}"
    if cache.get(lockout_key):
        return (
            False,
            "Pencarian untuk NIK ini dikunci sementara selama 15 menit akibat 5 kali kegagalan verifikasi berturut-turut.",
        )

    return True, ""


def record_nik_failed_attempt(nik: str) -> int:
    """
    Increments the consecutive failed attempt counter for a NIK.
    If it reaches NIK_LOCKOUT_MAX_FAILURES (5), sets a 15-minute lockout.
    Returns current failure count.
    """
    if not nik:
        return 0

    nik_digest = hash_nik(nik)
    fail_key = f"portal_fail_nik_{nik_digest}"
    lockout_key = f"portal_lockout_nik_{nik_digest}"

    current_fails = cache.get(fail_key)
    if current_fails is None:
        new_fails = 1
        cache.set(fail_key, new_fails, timeout=NIK_LOCKOUT_DURATION)
    else:
        try:
            new_fails = cache.incr(fail_key)
        except Exception:
            new_fails = int(current_fails) + 1
            cache.set(fail_key, new_fails, timeout=NIK_LOCKOUT_DURATION)

    if new_fails >= NIK_LOCKOUT_MAX_FAILURES:
        cache.set(lockout_key, True, timeout=NIK_LOCKOUT_DURATION)

    return new_fails


def reset_nik_failed_attempts(nik: str) -> None:
    """Resets the failure counter upon successful verification."""
    if not nik:
        return
    nik_digest = hash_nik(nik)
    cache.delete(f"portal_fail_nik_{nik_digest}")
    cache.delete(f"portal_lockout_nik_{nik_digest}")
