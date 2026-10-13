"""
Django 5.x Settings — Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini)
Kelurahan Jurangmangu Barat.

Hardened by default (Fail-Closed):
- Loads environment variables via python-dotenv (never hardcoded production secrets)
- Validates 32-byte AES-256-GCM key, HMAC-SHA256 pepper length, and Key Separation at startup
- Enforces Argon2 password hashing, bounded SimpleJWT lifetimes, and explicit CORS origins
- Attaches ZeroPiiLogFilter to prevent 16-digit NIK or JWT leakage in logs (UU PDP No. 27/2022)
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

from config.security import (
     validate_auth_guardrails,
    validate_secret_management,
)

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env if present, falling back to root .env
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

# --- 1. Environment & Fail-Closed Debug Flag ---
DEBUG = os.environ.get("DJANGO_DEBUG", "False").strip().lower() in ("true", "1", "yes")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-django-secret-key-do-not-use-in-production-env-9876543210",
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]

# --- 2. UU PDP Cryptographic Keys (AES-256-GCM & HMAC-SHA256) ---
NIK_AES_KEY_RAW = os.environ.get(
    "NIK_AES_KEY",
    "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
)
NIK_HMAC_PEPPER = os.environ.get(
    "NIK_HMAC_PEPPER",
    "pepper-jurangmangu-barat-hmac-sha256-dev-only-key-separation-2026",
)
PDF_DOWNLOAD_TOKEN_MAX_AGE_SECONDS = int(os.environ.get("PDF_DOWNLOAD_TOKEN_MAX_AGE_SECONDS", "900"))

# --- 3. CORS Configuration (Never allow wildcard '*') ---
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# Validate secrets, 32-byte AES-256 key, key separation, and CORS origins at startup
NIK_AES_KEY_BYTES = validate_secret_management(
    debug=DEBUG,
    django_secret_key=SECRET_KEY,
    nik_aes_key=NIK_AES_KEY_RAW,
    nik_hmac_pepper=NIK_HMAC_PEPPER,
    cors_allowed_origins=CORS_ALLOWED_ORIGINS,
    allowed_hosts=ALLOWED_HOSTS,
)

# --- 4. Installed Apps & Middleware ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_q",
    "core",
]

# Custom user model (StaffUser with role + rt_number)
AUTH_USER_MODEL = "core.StaffUser"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --- 5. Password Hashing (Argon2 first per OWASP recommendation) ---
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- 6. DRF & SimpleJWT Auth Guardrails (Fail-Closed by Default) ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
        "user": "120/min",
        "auth_login": os.environ.get("AUTH_LOGIN_RATE_LIMIT", "10/15m"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "30"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        hours=int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME_HOURS", "8"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Enforce Auth Guardrails at startup
validate_auth_guardrails(REST_FRAMEWORK, SIMPLE_JWT)

# --- 7. Security Headers, Cookie Hardening, & Upload Size Caps ---
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Cap Excel (.xlsx) upload and request payload memory to 5 MB (DoS Protection)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- 8. External Services (Gemini Flash XAI & Public Portal Anti-Bot) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
GEMINI_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "0.15"))
GEMINI_MAX_RETRIES = int(os.environ.get("GEMINI_MAX_RETRIES", "2"))

TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "")
PUBLIC_PORTAL_RATE_LIMIT_PER_MIN = int(os.environ.get("PUBLIC_PORTAL_RATE_LIMIT_PER_MIN", "5"))
PUBLIC_PORTAL_NIK_LOCKOUT_ATTEMPTS = int(os.environ.get("PUBLIC_PORTAL_NIK_LOCKOUT_ATTEMPTS", "5"))
PUBLIC_PORTAL_NIK_LOCKOUT_SECONDS = int(os.environ.get("PUBLIC_PORTAL_NIK_LOCKOUT_SECONDS", "900"))

# --- 9. Django-Q2 Async Worker Configuration ---
Q_CLUSTER = {
    "name": "bansos_xai_worker",
    "workers": 2,
    "timeout": 90,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}

# --- 10. Zero-PII Logging Filter (UU PDP Compliance) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "zero_pii": {
            "()": "config.security.ZeroPiiLogFilter",
        },
    },
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["zero_pii"],
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

LANGUAGE_CODE = "id-id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
