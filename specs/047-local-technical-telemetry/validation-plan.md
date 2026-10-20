# Validation plan

Each procedure uses temporary synthetic roots and the stdlib unittest runner. No native Codex/Claude process, provider, installation in user configuration, clean-room reproduction or experimental attempt is executed.

These retained procedures do not schedule another execution. Existing results in `../046-local-technical-telemetry/evidence/` are frozen historical records. Any separately authorized future result must use a distinct candidate-bound destination outside that historical folder and retain actual commands, counts, outputs and input hashes. A planned check is not obtained evidence; no historical log, receipt or manifest may be overwritten.

## procedure_privacy

REQ-001/SC-001: Default off; explicit local consent; collect only closed numeric aggregates, never content or identity. Include the success and corresponding absent/invalid/failing case.

## procedure_aggregation

REQ-002/SC-002: Count each covered boundary once; coarse duration histogram and four fixed analyzer classification totals with missing coverage explicit. Include the success and corresponding absent/invalid/failing case.

## procedure_storage

REQ-003/SC-003: Transactional SQLite outside repositories, private permissions, 30 UTC-day retention and at most 10 MiB including auxiliary files; no daemon. Include the success and corresponding absent/invalid/failing case.

## procedure_mcp

REQ-004/SC-004: Instrument ToolingService.invoke once, without changing tools, permissions, envelopes or runtime authority. Include the success and corresponding absent/invalid/failing case.

## procedure_cli

REQ-005/SC-005: Instrument analyze and analyze-git once, retaining their output and exit contracts, including failed input and cancellation. Include the success and corresponding absent/invalid/failing case.

## procedure_installation

REQ-006/SC-006: Expose off|local in serve and previewed lifecycle configuration, receipts and read-only diagnosis; skills never enable telemetry. Include the success and corresponding absent/invalid/failing case.

## procedure_exchange

REQ-007/SC-007: Provide text/JSON reports and strict, bounded manual incremental batches; deduplicate batches without a persistent installation ID; distinguish purge from uninstall. Include the success and corresponding absent/invalid/failing case.

## procedure_noninterference

REQ-008/SC-008: Collector faults never change product behavior; measure overhead and expose known/unknown loss; product aggregates do not satisfy native, experimental or acceptance gates. Include the success and corresponding absent/invalid/failing case.

## Candidate profiles

Run focused tests after each coherent increment, then `python3 scripts/validate_change.py --base develop --profile quick`; run the PR profile once on a stable candidate. Profile escalation is retained. A profile cannot satisfy native observations, clean-room reproduction, experimental accounting, independent review or founder acceptance. A dirty local source is not a frozen commit.

## Isolated parent and worker environment

Activate the isolated Python 3.12+ environment before running profiles so both the parent and bare `python3` worker commands resolve the same supported interpreter. On this macOS machine the unactivated system `python3` is 3.9.6; invoking only the venv interpreter does not change PATH for those workers. Profile commands also isolate system/global Git configuration. The independent clone requires the exact already-public corrected M4.5 autonomous tag from the ADR-0022 crosswalk in addition to the curated historical assurance refs. The environment diagnosis retains the failed controls and their corrected four-test result; no test/production Git behavior is weakened. This is setup for local repository checks, not a new SPEC-044/T004 reproduction.

## Follow-up correction validation

The [2026-10-16 local review](../046-local-technical-telemetry/review-20261016.md) adds an existing-export file-sync failure/retry control and a deterministic import path-to-symlink replacement control, plus fixed refusal when safe-open flags are absent, traced to REQ-007/SC-007 and the REQ-001/003 privacy/storage boundaries. The retained `../046-local-technical-telemetry/evidence/review-validation.json` binds the historical corrected-source controls, four negative mutations, descriptive overhead and quick/PR profiles from that review. Its identity is unchanged; it is not a destination for later results. Final task/count/draft packaging has its own structural and hash readback; it never upgrades independent/native/human acceptance.
