# Graph Report - BANSOS_SAW+LLM  (2026-10-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 940 nodes · 2185 edges · 81 communities (45 shown, 36 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 226 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ba8b567e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- App.tsx
- test_security_guardrails.py
- models.py
- AuditLog
- _add_evaluation
- test_api_endpoints.py
- core/urls.py
- test_saw_and_tiebreaker.py
- StaffUser
- xai_explainer.py
- SelectionResult
- views.py
- evaluation_metrics.py
- SelectionBatch
- pdf_generator.py
- package.json
- compilerOptions
- test_crypto_and_models.py
- Criteria
- serializers.py
- django_db
- django_db
- hash_nik
- Simple Additive Weighting (SAW)
- devDependencies
- test_pdf_and_evaluation.py
- excel_ingest.py
- test_xai_and_fallback.py
- crypto.py
- validate_nik
- build_anonymous_payload
- saw_engine.py
- decimal
- generate_deterministic_fallback
- resolve_rankings_with_tie_breaker
- process_batch_xai_task
- django_db
- run_e2e_verification.cjs
- Implementation Plan: Bansos SAW-XAI
- IsSuperAdmin
- dependencies
- CitizenCreateView
- export_batch_results_xlsx
- scripts
- Evaluation
- CriteriaBatchUpdateView
- test_generate_xai_for_evaluation_duck_typed_client_support
- vite.config.ts
- AGENTS.md
- XAI Narrative Generation (Gemini)
- Hybrid EDSS Architecture
- Backend Requirements
- Zero-Trust Privacy Model
- Executive Admin Dashboard Design
- Lurah Approval & PDF Preview Design
- XAI Gemini Narrative Generator Design
- Laporan Pengujian Bab 4 Skripsi
- Login Page UI (Desktop)
- Executive Dashboard UI (Desktop)
- SAW Ranking UI Screenshot
- Surveyor Input UI (Desktop)
- Public Portal UI (Desktop)
- Public Portal Result Screenshot
- Public Portal UI (Mobile)
- Executive Dashboard UI (Mobile)
- Navigation Drawer UI (Mobile)
- Criteria Management UI (Tablet)
- Full Layout UI (Desktop 1440px)
- Frontend Entry Point
- Project README

## God Nodes (most connected - your core abstractions)
1. `SelectionBatch` - 64 edges
2. `calculate_batch_saw()` - 52 edges
3. `Criteria` - 44 edges
4. `Evaluation` - 44 edges
5. `SelectionResult` - 40 edges
6. `AuditLog` - 37 edges
7. `StaffUser` - 36 edges
8. `EvaluationDetail` - 30 edges
9. `Citizen` - 29 edges
10. `Period` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Criteria & Weight Management Design` --references--> `ADR-003: Immutable Criteria & Tie-Breaker`  [INFERRED]
  .stitch/designs/manajemen-kriteria-bobot.png → docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md
- `Public Portal Cek Bansos Design` --references--> `ADR-004: Async XAI & Public Portal Security`  [INFERRED]
  .stitch/designs/portal-publik-cek-bansos.png → docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md
- `Criteria Management UI (Desktop)` --references--> `Simple Additive Weighting (SAW)`  [EXTRACTED]
  frontend/e2e_screenshots/03_criteria_management_desktop.png → .stitch/designs/manajemen-kriteria-bobot.html
- `SAW Ranking Table UI (Tablet)` --references--> `Simple Additive Weighting (SAW)`  [EXTRACTED]
  frontend/e2e_screenshots/13_tablet_768px_saw_table.png → .stitch/designs/manajemen-kriteria-bobot.html
- `SAW Ranking Table Design` --semantically_similar_to--> `Seleksi SAW & Ranking KPM`  [EXTRACTED] [semantically similar]
  .stitch/designs/seleksi-saw-ranking-kpm.png → .stitch/designs/seleksi-saw-ranking-kpm.html

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Data Privacy & Security Layer** — adr_002, adr_004, adr_006 [EXTRACTED 0.90]
- **XAI Fidelity & Safety Framework** — gemini_2_5_flash, zero_pii_sanitation, saw_algorithm [EXTRACTED 0.90]
- **Bansos Decision & Explanation Framework** — adr_001, adr_003, adr_006, hybrid_saw_xai_concept [EXTRACTED 0.95]
- **EDSS Bansos Adjudication Workflow** — stitch_designs_seleksi_saw_ranking_kpm_html, stitch_designs_generator_narasi_xai_gemini_html, stitch_designs_pengesahan_berita_acara_lurah_html, stitch_designs_portal_publik_cek_bansos_html [EXTRACTED 0.95]

## Communities (81 total, 36 thin omitted)

### Community 0 - "App.tsx"
Cohesion: 0.07
Nodes (56): App(), CriteriaManagementPage, ExecutiveDashboardPage, LoginPage, LurahApprovalPage, PageLoader(), PublicPortalPage, SawRankingPage (+48 more)

### Community 1 - "test_security_guardrails.py"
Cohesion: 0.07
Nodes (9): parse_aes_256_key(), scrub_sensitive_text(), validate_auth_guardrails(), validate_secret_management(), ZeroPiiLogFilter, test_auth_guardrails_reject_allow_any_and_unbounded_jwt(), test_parse_aes_256_key_strictly_enforces_32_bytes(), test_secret_management_enforces_key_separation_and_blocks_wildcard_cors() (+1 more)

### Community 2 - "models.py"
Cohesion: 0.08
Nodes (14): contains_plaintext_nik(), AliasQuerySet, AuditLogQuerySet, BatchCriteriaQuerySet, CitizenManager, CitizenQuerySet, _coerce_approved_by(), CriteriaQuerySet (+6 more)

### Community 3 - "AuditLog"
Cohesion: 0.07
Nodes (6): Action, AuditLog, EvaluationDetail, _remap_update_fields(), SubCriteria, test_adversarial_orm_queryset_aliases_and_null_tms_reason()

### Community 4 - "_add_evaluation"
Cohesion: 0.11
Nodes (20): _add_evaluation(), all_pass_quota_batch(), all_tms_batch(), incomplete_eligible_batch(), _make_batch(), _make_citizen(), _make_period(), _seed() (+12 more)

### Community 5 - "test_api_endpoints.py"
Cohesion: 0.11
Nodes (27): verify_pdf_download_token(), active_batch(), api_client(), _auth_client(), _create_sample_excel(), populated_batch(), published_batch_with_results(), _seed_db() (+19 more)

### Community 6 - "core/urls.py"
Cohesion: 0.08
Nodes (10): CitizenImportExcelView, PublicCheckStatusView, PublicResultPdfView, SelectionApproveView, SelectionBeritaAcaraPdfView, SelectionCalculateView, SelectionEvaluationMetricsView, SelectionGenerateXaiView (+2 more)

### Community 7 - "test_saw_and_tiebreaker.py"
Cohesion: 0.11
Nodes (13): calculate_batch_saw(), test_all_tms_batch_raises_validation_error(), test_approved_batch_rejects_recalculation(), test_calculate_batch_saw_creates_audit_log(), test_calculate_batch_saw_transitions_status_to_calculated(), test_incomplete_criteria_raises_validation_error(), test_nonexistent_batch_id_raises_does_not_exist(), test_post_calculation_weight_mutation_does_not_alter_frozen_snapshot() (+5 more)

### Community 8 - "StaffUser"
Cohesion: 0.12
Nodes (7): Role, StaffUser, IsStaff, IsSuperAdminOrSurveyor, IsSuperAdminOrViewer, IsSurveyor, IsViewer

### Community 9 - "xai_explainer.py"
Cohesion: 0.16
Nodes (3): generate_xai_for_evaluation(), map_explanation_to_public_schema(), validate_xai_output()

### Community 10 - "SelectionResult"
Cohesion: 0.11
Nodes (9): ExplanationSource, ResultStatus, SelectionResult, MockGeminiClient, _Models, test_xai_explainer_rejects_hallucinated_criteria_and_falls_back(), test_xai_explainer_rejects_malformed_json_and_falls_back(), test_xai_explainer_retries_and_falls_back_on_error() (+1 more)

### Community 11 - "views.py"
Cohesion: 0.10
Nodes (4): LoginSerializer, StaffLoginRateThrottle, StaffLoginView, XlsxRenderer

### Community 12 - "evaluation_metrics.py"
Cohesion: 0.15
Nodes (9): _canonical_sort_key(), compute_batch_evaluation_metrics(), detect_narrative_hallucinations(), export_thesis_evaluation_dataset(), export_thesis_evaluation_dataset_xlsx(), extract_primary_ai_criterion(), get_sus_questionnaire_template(), normalize_indonesian_numeric_text() (+1 more)

### Community 13 - "SelectionBatch"
Cohesion: 0.14
Nodes (4): Command, Command, SelectionBatch, Status

### Community 14 - "pdf_generator.py"
Cohesion: 0.11
Nodes (4): _build_kop_surat(), generate_berita_acara_pdf(), generate_individual_result_pdf(), _generate_qr_flowable()

### Community 15 - "package.json"
Cohesion: 0.10
Nodes (18): name, private, type, version, autoprefixer, axios, clsx, jsdom (+10 more)

### Community 16 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleResolution (+11 more)

### Community 17 - "test_crypto_and_models.py"
Cohesion: 0.13
Nodes (8): mask_name(), sign_pdf_download_token(), test_encrypt_nik_32byte_key_enforcement(), test_mask_name_multi_word(), test_mask_name_single_word(), test_nik_crypto_roundtrip_and_no_plaintext_at_rest(), test_nik_hash_is_deterministic(), test_pdf_token_expired_raises()

### Community 18 - "Criteria"
Cohesion: 0.15
Nodes (9): BatchCriteria, Citizen, Criteria, CriterionType, Meta, freeze_batch_criteria(), test_citizen_blocks_plaintext_nik_at_rest_and_enforces_prd_schema_constraints(), seeded_criteria() (+1 more)

### Community 19 - "serializers.py"
Cohesion: 0.17
Nodes (10): CriteriaItemUpdateSerializer, CriteriaSerializer, EvaluationDetailSerializer, Meta, PeriodSerializer, SelectionResultItemSerializer, StaffUserSerializer, SubCriteriaSerializer (+2 more)

### Community 20 - "django_db"
Cohesion: 0.12
Nodes (8): test_berita_acara_pdf_api_endpoint_rbac(), test_berita_acara_pdf_generation_content_and_audit_log(), test_evaluation_metrics_api_endpoint(), test_evaluation_metrics_xlsx_export(), test_fidelity_hallucination_metrics_and_signed_pdf_download(), test_hallucination_rate_normalizes_indonesian_decimals_and_percentages(), test_individual_result_pdf_generation_masks_pii(), test_public_individual_pdf_endpoint_guards()

### Community 21 - "django_db"
Cohesion: 0.12
Nodes (8): test_fallback_borderline_tie_break_when_all_gaps_non_positive(), test_map_explanation_to_public_schema_handles_existing_public_keys_and_edge_cases(), test_security_audit_zero_pii_in_llm_prompt_and_network_payload(), test_validate_xai_output_extracts_primary_criterion_code_for_fidelity(), test_validate_xai_output_rejects_hallucinated_code_in_summary_or_recommendation(), test_validate_xai_output_rejects_hallucinated_decimal_score(), test_validate_xai_output_rejects_hallucinated_numbers_rank_and_quota(), test_validate_xai_output_strips_markdown_code_fences()

### Community 22 - "hash_nik"
Cohesion: 0.19
Nodes (6): hash_nik(), check_ip_rate_limit(), check_nik_lockout(), record_nik_failed_attempt(), reset_nik_failed_attempts(), verify_turnstile_captcha()

### Community 23 - "Simple Additive Weighting (SAW)"
Cohesion: 0.12
Nodes (16): Celery Task Queue, SAW Ranking Table Design, Criteria Management UI (Desktop), SAW Ranking Table UI (Tablet), Google Gemini 2.5 Flash, Hierarchical Tie-Breaker (FR-07), Simple Additive Weighting (SAW), Generator Narasi XAI (Gemini) (+8 more)

### Community 24 - "devDependencies"
Cohesion: 0.12
Nodes (16): devDependencies, autoprefixer, jsdom, playwright, postcss, tailwindcss, @testing-library/jest-dom, @testing-library/react (+8 more)

### Community 25 - "test_pdf_and_evaluation.py"
Cohesion: 0.21
Nodes (8): Period, _create_citizen(), narrated_batch(), _seed_db(), superadmin_user(), surveyor_user(), test_fidelity_score_formula_and_zero_division_guard(), viewer_user()

### Community 26 - "excel_ingest.py"
Cohesion: 0.16
Nodes (4): check_surveyor_rt_scope(), normalize_rt(), import_citizens_from_excel(), SelectionMarkRtSubmittedView

### Community 27 - "test_xai_and_fallback.py"
Cohesion: 0.24
Nodes (8): _add_evaluation(), calculated_batch_with_evaluations(), _make_batch(), _make_citizen(), _seed(), test_anonymous_payload_rejects_disqualified_or_uncalculated(), test_anonymous_payload_zero_passed_or_all_passed(), test_process_batch_xai_task_rejects_invalid_batch_status()

### Community 28 - "crypto.py"
Cohesion: 0.17
Nodes (3): decrypt_nik(), _resolve_aes_key(), _resolve_hmac_pepper()

### Community 29 - "validate_nik"
Cohesion: 0.19
Nodes (5): encrypt_nik(), mask_nik(), validate_nik(), test_mask_nik_format(), test_security_audit_unicode_nik_and_tampered_ciphertext_rejected()

### Community 30 - "build_anonymous_payload"
Cohesion: 0.15
Nodes (6): build_anonymous_payload(), test_anonymous_payload_contains_zero_pii_and_uses_frozen_weights(), test_anonymous_payload_criteria_data_fields_and_avg_passed_score(), test_fallback_selects_highest_weighted_gap_and_maps_public_keys(), test_sanitizer_falls_back_to_batch_cutoff_score(), test_sanitizer_rejects_incomplete_evaluation_details()

### Community 31 - "saw_engine.py"
Cohesion: 0.19
Nodes (5): _normalize_benefit(), _normalize_cost(), validate_criteria_weights(), test_saw_accepts_valid_weight_sum(), test_saw_rejects_invalid_weight_sum()

### Community 32 - "decimal"
Cohesion: 0.21
Nodes (3): Migration, Migration, Migration

### Community 33 - "generate_deterministic_fallback"
Cohesion: 0.26
Nodes (6): _canonical_sort_key(), generate_deterministic_fallback(), _generate_lolos_narrative(), _generate_tidak_lolos_narrative(), test_fallback_canonical_tie_break_order_c1_to_c4(), test_fallback_for_status_lolos()

### Community 34 - "resolve_rankings_with_tie_breaker"
Cohesion: 0.23
Nodes (5): resolve_rankings_with_tie_breaker(), _tie_break_level(), _to_decimal(), test_tie_breaker_empty_candidates_returns_empty(), test_tie_breaker_none_and_missing_keys_handled_robustly()

### Community 35 - "process_batch_xai_task"
Cohesion: 0.18
Nodes (5): process_batch_xai_task(), test_process_batch_xai_task_blocks_narrated_status_when_generation_fails_partially(), test_process_batch_xai_task_skips_already_narrated_candidates_idempotently(), test_process_batch_xai_task_transitions_to_narrated(), test_process_batch_xai_task_with_single_evaluation_id()

### Community 36 - "django_db"
Cohesion: 0.18
Nodes (5): test_adversarial_citizen_at_rest_guards_on_hash_mask_update_and_bulk_create(), test_adversarial_crypto_base64_malleability_and_override_settings(), test_citizen_upsert_idempotency(), test_invalid_nik_rejected(), test_seed_initial_data_creates_criteria()

### Community 37 - "run_e2e_verification.cjs"
Cohesion: 0.18
Nodes (7): { chromium }, { execSync }, fs, path, SCREENSHOT_DIR, VIEWPORTS, playwright

### Community 38 - "Implementation Plan: Bansos SAW-XAI"
Cohesion: 0.22
Nodes (10): ADR-001: Hybrid SAW-XAI Architecture, ADR-002: NIK Cryptography & Zero-PII, ADR-003: Immutable Criteria & Tie-Breaker, ADR-004: Async XAI & Public Portal Security, ADR-005: Responsive UI & Design Gate, ADR-006: PDF Decryption & Thesis Metrics, Criteria & Weight Management Design, Public Portal Cek Bansos Design (+2 more)

### Community 39 - "IsSuperAdmin"
Cohesion: 0.27
Nodes (3): IsSuperAdmin, SelectionBatchSerializer, BatchListView

### Community 40 - "dependencies"
Cohesion: 0.25
Nodes (8): dependencies, axios, clsx, lucide-react, react, react-dom, react-router-dom, tailwind-merge

### Community 41 - "CitizenCreateView"
Cohesion: 0.33
Nodes (3): CitizenCreateSerializer, PublicCheckStatusRequestSerializer, CitizenCreateView

### Community 43 - "scripts"
Cohesion: 0.33
Nodes (6): scripts, build, dev, preview, test, test:watch

### Community 44 - "Evaluation"
Cohesion: 0.40
Nodes (3): EligibilityStatus, Evaluation, TmsReason

### Community 49 - "XAI Narrative Generation (Gemini)"
Cohesion: 0.67
Nodes (3): XAI Narrative Generation (Gemini), XAI Generator UI (Desktop), Lurah Approval UI (Desktop)

## Knowledge Gaps
- **51 isolated node(s):** `autoprefixer`, `clsx`, `jsdom`, `postcss`, `tailwind-merge` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 429 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SelectionBatch` connect `SelectionBatch` to `models.py`, `AuditLog`, `_add_evaluation`, `test_api_endpoints.py`, `core/urls.py`, `test_saw_and_tiebreaker.py`, `xai_explainer.py`, `views.py`, `evaluation_metrics.py`, `pdf_generator.py`, `test_crypto_and_models.py`, `Criteria`, `serializers.py`, `django_db`, `test_pdf_and_evaluation.py`, `excel_ingest.py`, `test_xai_and_fallback.py`, `saw_engine.py`, `process_batch_xai_task`, `IsSuperAdmin`, `CitizenCreateView`, `export_batch_results_xlsx`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `SelectionBatch` (e.g. with `Command` and `CitizenCreateSerializer`) actually correct?**
  _`SelectionBatch` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `autoprefixer`, `clsx`, `jsdom` to the rest of the system?**
  _51 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.0725760183591509 - nodes in this community are weakly interconnected._
- **Why does `calculate_batch_saw()` connect `test_saw_and_tiebreaker.py` to `resolve_rankings_with_tie_breaker`, `AuditLog`, `_add_evaluation`, `test_api_endpoints.py`, `core/urls.py`, `xai_explainer.py`, `SelectionResult`, `views.py`, `Evaluation`, `SelectionBatch`, `Criteria`, `test_pdf_and_evaluation.py`, `test_xai_and_fallback.py`, `saw_engine.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `calculate_batch_saw()` (e.g. with `AuditLog` and `BatchCriteria`) actually correct?**
  _`calculate_batch_saw()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_security_guardrails.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06794871794871794 - nodes in this community are weakly interconnected._