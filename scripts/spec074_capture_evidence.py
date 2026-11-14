# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 (BL.4): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. Procedures are added as their tasks land (T002: procedure_001; T003: procedure_002; T004: procedure_003; T005: procedure_004; T006: procedure_005; T007: procedure_006).

    python -m scripts.spec074_capture_evidence [procedure_NNN ...]

Naming procedures re-runs only those; the default re-runs every procedure.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/074-lightning-trace-consent"
EVIDENCE = SPEC / "evidence"
PROCEDURES = {
    'procedure_001': {
        "scenario": 'SC-001',
        "modules": ["tests.test_spec074_consent_config", "tests.test_lightning_config"],
        "inputs": ["agent_braid/lightning_config.py", "agent_braid/lightning_cli.py", "agent_braid/lightning_store.py",
                   "agent_braid/plugin_registry.py", "schemas/0.3.0-experimental/lightning-config.schema.json",
                   "tests/test_spec074_consent_config.py", "tests/test_lightning_config.py"],
        "outcome_note": "T002 part: traces.contentConsent accepts only none and redacted and defaults to none with a null consent record; a BL.0 profile without consentedAt and consentPreviewDigest reads as none. `lightning init --trace-consent redacted [--trace-sources ...]` previews level, consentedAt, sources (host-transcript only when listed, OD-1), retention, redaction classes (email as a per-run salted hash, OD-2), storage, residual risk and no expiry (OD-3); apply with the matching --preview-digest writes consentedAt and that digest. Unrelated changes keep the record, new sources renew it, lowering to none clears it, and `lightning status` shows level, consentedAt, sources and expires null. The schema and the validator agree on a valid and invalid corpus. Negative controls: raw, a record without consent, consent without a record, an answered record field, a stale or forged digest (nothing written), and plugin setup lab/off leave the profile byte-identical; the store refuses content without consent (store-consent).",
        "limits": "Temporary homes; no content is collected (the store gate is T003, redaction T004). Calendar validity of consentedAt (for example 2026-02-30) is checked by the validator only; the schema checks the YYYY-MM-DD shape. The per-run email salt itself is implemented with the redactor (T004).",
    },
    'procedure_002': {
        "scenario": 'SC-002',
        "modules": ["tests.test_spec074_consent_gate", "tests.test_lightning_store", "tests.test_lightning_cli"],
        "inputs": ["agent_braid/lightning_adapter.py", "agent_braid/lightning_store.py", "agent_braid/lightning_cli.py",
                   "agent_braid/lightning_config.py", "tests/test_spec074_consent_gate.py",
                   "tests/test_lightning_store.py", "tests/test_lightning_cli.py"],
        "outcome_note": "T003: with no profile, consent none, or an invalid profile (unparseable, redacted without its consent record, an unknown level) the store refuses a content-bearing record with store-consent and writes nothing, and the adapter gate and `lightning status` traceContent report content-consent-required; status itself refuses an invalid profile with its config-* code. An explicit content_consent none overrides a redacted profile, and an unknown explicit level is refused. With consent redacted the gate opens only for listed sources (others: source-not-consented), and a record that stays unclean after redaction is refused with redaction-incomplete, leaving only a content-free stub (C2: redact on ingest). Negative control: invalid configuration never reads as redacted. Content-free kinds are unchanged (SPEC-070 store suite).",
        "limits": "Temporary homes; no content is read or stored. The gate is the adapter's entry check; it reads rollout and Loom sources since T007 (procedure_006). Content storage with consent, redaction and retention is procedure_005 (T006).",
    },
    'procedure_003': {
        "scenario": 'SC-003',
        "modules": ["tests.test_lightning_redact"],
        "inputs": ["agent_braid/lightning_redact.py", "agent_braid/lightning_hosts.py", "tests/test_lightning_redact.py"],
        "outcome_note": "T004: lightning_redact detects, then replaces, each class with its typed placeholder: literal known secret [REDACTED:secret], API key and token shapes [REDACTED:token], bearer header [REDACTED:bearer], private key block [REDACTED:private-key], email [REDACTED:email:<8-hex>] (HMAC-SHA256 with a 16-byte per-run salt: stable within a run, case-insensitive, different across salts, OD-2) and the home path as a ~ prefix; the post-redaction scan is clean. JSON values are redacted in keys and strings and scanned in serialized form. An unclean result is refused with redaction-incomplete without echoing the match. Negative control: each sample must be detected by the scan before redaction, so a disabled pattern fails. The SPEC-069 driver's SECRET_PATTERNS is the same object (single source), unchanged pattern for pattern.",
        "limits": "Synthetic samples only; encoded forms are covered by the T005 canary corpus (procedure_004). Redaction is pattern-based: secrets of unknown shape that are not known literals are not caught (privacy review residual risk). The store calls the redactor on ingest since T006 (procedure_005).",
    },
    'procedure_004': {
        "scenario": 'SC-004',
        "modules": ["tests.test_spec074_canary_corpus", "tests.test_lightning_redact"],
        "inputs": ["agent_braid/lightning_redact.py", "scripts/spec074_canary_corpus.py",
                   "tests/fixtures/spec074-canaries/corpus.json", "tests/test_spec074_canary_corpus.py",
                   "tests/test_lightning_redact.py"],
        "outcome_note": "T005: the committed corpus (tests/fixtures/spec074-canaries/corpus.json, regenerated byte-for-byte by scripts/spec074_canary_corpus.py) holds 13 synthetic canaries covering every class (literal secret, seven token shapes, bearer, private key, email, home path) in five forms (plain, JSON-escaped, URL-encoded, split across two fields, base64): 65 records. Every record is detected by the scan, and every one is either redacted with a clean post-scan and no canary value in the output or any decoded view of it (URL-decoded, \\u-unescaped, base64-decoded, fields joined), or refused with redaction-incomplete. URL-encoded, \\u-escaped and base64 runs that hide a hit become [REDACTED:encoded]; a hidden split (no recognizable prefix in the first field) is refused. Negative control: with base64 decoding disabled a base64 canary reaches the output, so the corpus test reports it.",
        "limits": "The corpus bounds the claim: only these synthetic shapes and five encodings are tested; nested or double encodings, other alphabets, and secrets of unknown shape are residual risks (privacy review). A split whose first field already shows a recognizable prefix is redacted per field; its tail fragment in the next field is not recognizable and is kept. The store calls the redactor on ingest since T006 (procedure_005).",
    },
    'procedure_005': {
        "scenario": 'SC-005',
        "modules": ["tests.test_spec074_retention_purge", "tests.test_spec074_consent_gate", "tests.test_lightning_store"],
        "inputs": ["agent_braid/lightning_store.py", "agent_braid/lightning_cli.py", "agent_braid/lightning_redact.py",
                   "tests/test_spec074_retention_purge.py", "tests/test_spec074_consent_gate.py",
                   "tests/test_lightning_store.py"],
        "outcome_note": "T006: with consent redacted the store redacts each content record on ingest with a per-run 16-byte email salt (email.salt, 0600) and appends {createdAt, record} to traces.jsonl; an unclean record is refused with redaction-incomplete and leaves only a {createdAt, refused} stub. With an injected clock, sweep (store.sweep, `lightning sweep`, and every content append for its own run) removes runs created before the retention cutoff and content lines older than it in the remaining runs; retention outside 1-90 is refused with retention-out-of-range. `lightning purge --run-id <id> | --all` previews the runs and content bytes with a previewDigest and deletes nothing; `--apply --preview-digest` with a stale or forged digest is refused with preview-stale; a matching apply deletes each run directory (records, content, salt, lock) and leaves no content bytes in the store, while files outside the run store are untouched. Negative control: with the content sweep disabled the expired record survives.",
        "limits": "Temporary homes and synthetic content; the clock is injected (createdAt values), not waited. The sweep runs on `lightning sweep`, `purge --expired` and content appends; reading a run does not sweep it. Purge deletes Braid Lightning run directories only; host transcripts, Loom and System One are never written by the store.",
    },
    'procedure_006': {
        "scenario": 'SC-006',
        "modules": ["tests.test_lightning_adapter", "tests.test_spec074_consent_gate", "tests.test_lightning_cli"],
        "inputs": ["agent_braid/lightning_adapter.py", "agent_braid/lightning_redact.py", "agent_braid/lightning_store.py",
                   "agent_braid/lightning_schema.py", "agent_braid/view_loom.py",
                   "tests/fixtures/view/loom/valid-corpus.jsonl", "tests/test_lightning_adapter.py",
                   "tests/test_spec074_consent_gate.py", "tests/test_lightning_cli.py"],
        "outcome_note": "T007: lightning_adapter turns one attempt's SPEC-070 events plus its redacted content records into braid-lightning-triplet/v0.1 records, one per model_request, and braid-lightning-messages/v0.1 user and assistant turns; the committed Loom corpus becomes one triplet per strand and one system message per event. Every text is redacted with the run salt and post-scanned (redaction classes counted), and each record carries source, sourceSha256 and sorted loss notes. Rewards match by first-occurrence (nearest earlier unrewarded request) or first-sibling (others refused with reward-match); a second content record for one request is ignored with content-duplicate. Outputs are deterministic for the same inputs and salt. Without consent, or for an unlisted source, prompt, response and messages are null or empty with content-consent-required while rewards stay. An unparseable Loom stream or an unknown attempt is refused with source-invalid. Negative control: with redaction switched off a canary in a Loom label reaches the output and the clean check fails.",
        "limits": "Rollout and Loom sources only, synthetic content in temporary homes; host transcripts and System One episodes are T008 (procedure_006 is recaptured then). Loom carries no model text or reward, which the loss notes state. Refused content stubs carry no attempt, so content-refused is a run-level note. Redaction limits are those of procedure_003 and procedure_004.",
    },
}


def sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(modules: list[str]) -> dict:
    command = [sys.executable, "-m", "unittest", *modules]
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    tail = process.stderr.strip().splitlines()[-3:]
    ran = re.search(r"Ran (\d+) tests?", process.stderr)
    return {"command": "python -m unittest " + " ".join(modules), "returncode": process.returncode,
            "testsRun": int(ran.group(1)) if ran else None, "result": tail[-1] if tail else ""}


def main(argv: list[str] | None = None) -> int:
    selected = (sys.argv[1:] if argv is None else argv) or list(PROCEDURES)
    unknown = set(selected) - set(PROCEDURES)
    if unknown:
        print("unknown procedure: " + ", ".join(sorted(unknown)), file=sys.stderr)
        return 2
    EVIDENCE.mkdir(exist_ok=True)
    assurance_path = SPEC / "assurance.json"
    assurance = json.loads(assurance_path.read_text())
    scenarios = {s["id"]: s for r in assurance["requirements"] for s in r["scenarios"]}
    status = 0
    for name in selected:
        spec = PROCEDURES[name]
        result = run(spec["modules"])
        passed = result["returncode"] == 0 and result["result"].startswith("OK")
        record = {
            "procedure": name, "scenario": spec["scenario"], "specification": "SPEC-074 BL.4",
            "command": result["command"], "testsRun": result["testsRun"], "result": result["result"],
            "outcome": ("passed: " if passed else "FAILED: ") + spec["outcome_note"],
            "limits": spec["limits"],
            "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
            "inputs": {path: sha(path) for path in sorted(set(spec["inputs"]))},
        }
        path = EVIDENCE / f"{name}.json"
        path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        relative = path.relative_to(ROOT).as_posix()
        scenarios[spec["scenario"]]["obtained_evidence"] = [{
            "command": result["command"], "limits": spec["limits"], "outcome": record["outcome"],
            "path": relative, "sha256": sha(relative)}]
        print(f"{name}: {result['result']} ({result['testsRun']} tests)")
        status |= 0 if passed else 1
    assurance_path.write_text(json.dumps(assurance, indent=2, sort_keys=True) + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
