"""
core/services/xai_explainer.py — Google Gemini Flash Explainable AI Client with Fallback Switch.

PRD References:
  - FR-04: Asynchronous XAI generation using Google Gemini Flash (temperature=0.15, application/json).
  - FR-05: Deterministic fallback after 2 failed retries with exponential backoff (no HTTP 500).
  - Section 8.2: Official Dinas Sosial Kelurahan Jurangmangu Barat System Instruction.
  - Zero-PII: Only sanitized anonymous payloads are transmitted.
  - Anti-Hallucination: Validates output JSON and cross-checks active criteria codes.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from django.conf import settings
from django.utils import timezone

from core.models import Evaluation, SelectionResult
from core.services.deterministic_fallback import generate_deterministic_fallback
from core.services.sanitizer import build_anonymous_payload

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """Anda adalah asisten resmi Dinas Sosial Kelurahan Jurangmangu Barat yang bertugas memberikan penjelasan transparansi keputusan seleksi bantuan sosial berdasarkan kalkulasi matematis Simple Additive Weighting (SAW).

Pedoman Komunikasi dan Output:
1. Bersikaplah objektif, empati, santun, dan solutif. Jangan pernah menggunakan kata-kata yang mendiskreditkan warga.
2. Rujuk pemohon sebagai "Bapak/Ibu Pemohon". Jangan pernah mengarang data identitas di luar parameter JSON.
3. Jika status pemohon 'TIDAK_LOLOS':
   - Jelaskan bahwa pemohon berada di peringkat {rank} dari kuota {quota} penerima manfaat yang tersedia pada periode ini.
   - Lakukan analisis counterfactual: sebutkan 1 atau 2 kriteria yang menjadi faktor pembeda utama (jarak skor normalisasi terbesar dibanding rata-rata penerima yang lolos kuota).
   - Berikan rekomendasi edukatif yang konstruktif (misal: jika ada pemutakhiran data kondisi tanggungan atau ekonomi di masa mendatang, dapat melapor ke pihak RT untuk periode seleksi selanjutnya).
4. Jika status pemohon 'LOLOS':
   - Ucapkan selamat dan jelaskan kriteria apa yang menjadi pertimbangan prioritas utama sesuai bobot preferensi kelurahan.
   - Ingatkan jadwal verifikasi fisik berkas atau penyaluran di kantor kelurahan.
5. Keluarkan output dalam format JSON valid dengan field:
   - "ringkasan_keputusan": string (1 kalimat formal)
   - "faktor_penentu_utama": list of string
   - "narasi_lengkap": string (2-3 paragraf bahasa Indonesia mengalir)
   - "rekomendasi_tindak_lanjut": string
"""

CRITERION_CODE_PATTERN = re.compile(r"\bC\d+\b", re.IGNORECASE)


def validate_xai_output(
    data: Any,
    allowed_criteria_codes: set[str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate Gemini Flash JSON output against required fields, active criteria codes,
    and payload numeric consistency (preventing hallucination per PRD Section 11.2).

    Args:
        data: Parsed dict or raw JSON string from Gemini response.
        allowed_criteria_codes: Set of active criteria codes (e.g. {'C1', 'C2', 'C3', 'C4'}).
        payload: Optional anonymous payload dict for verifying numeric fidelity (rank, quota, scores).

    Returns:
        dict: Validated explanation dictionary.

    Raises:
        ValueError: If JSON is invalid, fields are missing/empty, or hallucinated codes/numbers appear.
    """
    if isinstance(data, str):
        cleaned = data.strip()
        # Strip markdown code blocks (e.g. ```json ... ```) if present
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        try:
            data = json.loads(cleaned)
        except Exception as exc:
            raise ValueError(f"Output bukan JSON valid: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Output Gemini wajib berupa dictionary JSON.")

    required_keys = {
        "ringkasan_keputusan": str,
        "faktor_penentu_utama": list,
        "narasi_lengkap": str,
        "rekomendasi_tindak_lanjut": str,
    }

    for key, expected_type in required_keys.items():
        if key not in data:
            raise ValueError(f"Field wajib '{key}' hilang dari output XAI.")
        val = data[key]
        if not isinstance(val, expected_type):
            raise ValueError(f"Field '{key}' harus bertipe {expected_type.__name__}, didapat {type(val).__name__}.")
        if expected_type is str and not val.strip():
            raise ValueError(f"Field string '{key}' tidak boleh kosong.")
        if expected_type is list and not val:
            raise ValueError(f"Field list '{key}' tidak boleh kosong.")

    # Compose full text from all 4 fields to prevent partial validation evasion
    factors_text = " ".join(str(f) for f in data["faktor_penentu_utama"])
    all_text = f"{data['ringkasan_keputusan']} {factors_text} {data['narasi_lengkap']} {data['rekomendasi_tindak_lanjut']}"

    # Anti-hallucination check for criteria codes
    if allowed_criteria_codes:
        normalized_allowed = {code.upper() for code in allowed_criteria_codes}

        # Extract all criterion codes mentioned (e.g., C99, C5)
        found_codes = {c.upper() for c in CRITERION_CODE_PATTERN.findall(all_text)}
        hallucinated_codes = found_codes - normalized_allowed
        if hallucinated_codes:
            raise ValueError(
                f"Halusinasi kode kriteria terdeteksi: {hallucinated_codes}. "
                f"Kriteria valid yang diizinkan: {normalized_allowed}."
            )

        # Anti-hallucination check for deprecated Crips/Criteria labels (e.g. 'Daya Listrik')
        if "daya listrik" in all_text.lower():
            raise ValueError("Halusinasi kriteria terdeteksi: 'Daya Listrik' bukan kriteria bansos aktif.")

    # Anti-hallucination check for numbers against payload (PRD Section 11.2)
    if payload:
        # Check rank fidelity if explicitly mentioned
        rank_matches = re.findall(r"peringkat\s+(\d+)", all_text, re.IGNORECASE)
        expected_rank = payload.get("rank")
        if expected_rank is not None:
            for rm in rank_matches:
                if int(rm) != int(expected_rank):
                    raise ValueError(
                        f"Halusinasi angka terdeteksi: teks menyebutkan peringkat {rm}, "
                        f"padahal peringkat pemohon adalah {expected_rank}."
                    )

        # Check quota fidelity if explicitly mentioned
        quota_matches = re.findall(r"kuota\s+(\d+)", all_text, re.IGNORECASE)
        expected_quota = payload.get("quota")
        if expected_quota is not None:
            for qm in quota_matches:
                if int(qm) != int(expected_quota):
                    raise ValueError(
                        f"Halusinasi angka terdeteksi: teks menyebutkan kuota {qm}, "
                        f"padahal kuota alokasi adalah {expected_quota}."
                    )

        # Check floating score decimals (e.g. 0.xxxx) against valid payload values
        valid_decimals: set[float] = set()
        for k in ("final_score", "cutoff_score"):
            if payload.get(k) is not None:
                valid_decimals.add(round(float(payload[k]), 4))
                valid_decimals.add(round(float(payload[k]), 2))
        for c in payload.get("criteria_data", []):
            for ck in ("weight", "normalized_score", "avg_passed_score"):
                if c.get(ck) is not None:
                    valid_decimals.add(round(float(c[ck]), 4))
                    valid_decimals.add(round(float(c[ck]), 2))

        found_decimals = re.findall(r"\b0\.\d+\b", all_text)
        for dec_str in found_decimals:
            dec_val = float(dec_str)
            if not any(abs(dec_val - vd) <= 0.01 for vd in valid_decimals):
                raise ValueError(
                    f"Halusinasi nilai numerik terdeteksi: angka desimal {dec_str} "
                    "tidak ditemukan pada parameter skor payload."
                )

    # Extract primary_criterion_code for academic thesis Fidelity Score evaluation (PRD Section 11.2)
    if "primary_criterion_code" not in data:
        factors = data.get("faktor_penentu_utama", [])
        if factors and isinstance(factors, list):
            match = CRITERION_CODE_PATTERN.search(str(factors[0]))
            if match:
                data["primary_criterion_code"] = match.group(0).upper()

    return data


def map_explanation_to_public_schema(ai_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Map internal Gemini/Fallback JSON keys to the public API schema contract (PRD Section 10.6).

    Internal keys:
      - ringkasan_keputusan
      - faktor_penentu_utama
      - narasi_lengkap
      - rekomendasi_tindak_lanjut

    Public schema keys:
      - ringkasan
      - faktor_utama
      - narasi_lengkap
      - rekomendasi
    """
    if not isinstance(ai_payload, dict):
        return {
            "ringkasan": "",
            "faktor_utama": [],
            "narasi_lengkap": "",
            "rekomendasi": "",
        }

    return {
        "ringkasan": ai_payload.get("ringkasan_keputusan") or ai_payload.get("ringkasan", ""),
        "faktor_utama": ai_payload.get("faktor_penentu_utama") or ai_payload.get("faktor_utama", []),
        "narasi_lengkap": ai_payload.get("narasi_lengkap", ""),
        "rekomendasi": ai_payload.get("rekomendasi_tindak_lanjut") or ai_payload.get("rekomendasi", ""),
    }


def generate_xai_for_evaluation(
    evaluation_id: int,
    gemini_client: Any = None,
    backoff_seconds: float = 1.0,
) -> SelectionResult:
    """
    Generate an XAI narrative for an Evaluation using Gemini Flash API, with automatic
    deterministic fallback after 2 retries with exponential backoff.

    Args:
        evaluation_id: PK of the Evaluation.
        gemini_client: Optional mock or existing google.genai.Client instance.
        backoff_seconds: Base backoff multiplier (0 in tests for fast execution).

    Returns:
        SelectionResult: Updated instance with ai_narrative, ai_payload_response,
                         and explanation_source.
    """
    payload = build_anonymous_payload(evaluation_id)
    eval_obj = Evaluation.objects.select_related("result").get(pk=evaluation_id)
    result = eval_obj.result

    allowed_codes = {item["code"] for item in payload.get("criteria_data", [])}
    max_retries = getattr(settings, "GEMINI_MAX_RETRIES", 2)
    model_name = getattr(settings, "GEMINI_MODEL_NAME", "gemini-2.5-flash")
    api_key = getattr(settings, "GEMINI_API_KEY", "")

    client = gemini_client
    if client is None:
        if api_key:
            try:
                from google import genai

                client = genai.Client(api_key=api_key, http_options={"timeout": 10.0})
            except Exception as exc:
                logger.warning("Gagal menginisialisasi Google GenAI Client: %s", exc)
                client = None
        else:
            client = None

    # If client is not available, immediately generate deterministic fallback
    if client is None:
        logger.info("Gemini API Client tidak tersedia. Menggunakan Deterministic Fallback.")
        fallback_data = generate_deterministic_fallback(payload)
        result.ai_payload_response = fallback_data
        result.ai_narrative = fallback_data["narasi_lengkap"]
        result.explanation_source = SelectionResult.ExplanationSource.DETERMINISTIC_FALLBACK
        result.narrated_at = timezone.now()
        result.save(update_fields=["ai_payload_response", "ai_narrative", "explanation_source", "narrated_at", "updated_at"])
        return result

    # Call Gemini API with retries and exponential backoff
    attempts = 1 + max_retries
    for attempt in range(attempts):
        try:
            temperature = float(getattr(settings, "GEMINI_TEMPERATURE", 0.15))
            # Build config using google.genai.types if available
            try:
                from google.genai import types

                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=temperature,
                    response_mime_type="application/json",
                )
            except ImportError:
                config = {
                    "system_instruction": SYSTEM_INSTRUCTION,
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                }

            user_prompt = json.dumps(payload, ensure_ascii=False)

            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=config,
                )
            elif hasattr(client, "generate"):
                response = client.generate(user_prompt)
            else:
                raise AttributeError("Client Gemini tidak memiliki metode 'models.generate_content' atau 'generate'.")

            if isinstance(response, str):
                response_text = response
            elif isinstance(response, dict):
                response_text = json.dumps(response)
            else:
                response_text = getattr(response, "text", "")

            validated = validate_xai_output(
                response_text,
                allowed_criteria_codes=allowed_codes,
                payload=payload,
            )

            # Success
            result.ai_payload_response = validated
            result.ai_narrative = validated["narasi_lengkap"]
            result.explanation_source = SelectionResult.ExplanationSource.GEMINI_API
            result.narrated_at = timezone.now()
            result.save(update_fields=["ai_payload_response", "ai_narrative", "explanation_source", "narrated_at", "updated_at"])
            return result

        except Exception as exc:
            logger.warning("Percobaan %d/%d Gemini Flash XAI gagal: %s", attempt + 1, attempts, exc)
            if attempt < max_retries:
                if backoff_seconds > 0:
                    sleep_time = backoff_seconds * (2**attempt)
                    time.sleep(sleep_time)
                continue

    # All retries exhausted -> Deterministic Fallback (FR-05: never throw HTTP 500)
    logger.info("Percobaan Gemini API habis. Mengalihkan ke Deterministic Fallback.")
    fallback_data = generate_deterministic_fallback(payload)
    result.ai_payload_response = fallback_data
    result.ai_narrative = fallback_data["narasi_lengkap"]
    result.explanation_source = SelectionResult.ExplanationSource.DETERMINISTIC_FALLBACK
    result.narrated_at = timezone.now()
    result.save(update_fields=["ai_payload_response", "ai_narrative", "explanation_source", "narrated_at", "updated_at"])
    return result
