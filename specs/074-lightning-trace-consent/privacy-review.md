# SPEC-074: Privacy review

Draft for owner review; not an approval.

## Data inventory

| Data | Source | Contains | Stored where | Retention |
|---|---|---|---|---|
| rollout events | SPEC-071 runner | prompts, responses, tool calls, rewards | plugin home `lightning/runs/<id>/` (owner-only) | 30 days default, ≤ 90 |
| host transcripts | Claude Code, Codex, OpenCode local logs | user prompts, code, paths, possibly secrets | read in place, never copied unredacted | host-controlled |
| Loom stream | Loom viewer events | activity metadata, labels | read in place | Loom-controlled |
| System One episodes | shadow store | prompts and advisory answers | read in place, read-only | 30 days (SPEC-066) |
| triplets/messages | adapter output | redacted text, rewards | run directory | same as rollouts |
| telemetry | ADR 0025 | counts, refusal reasons, no content | unchanged | unchanged |

## Threats

| ID | Threat |
|---|---|
| TH-1 | secret or token in a prompt stored or exported |
| TH-2 | personal data (emails, home paths, names in paths) retained |
| TH-3 | content collected without the owner knowing (silent default) |
| TH-4 | retention exceeded through a failed sweep |
| TH-5 | adapter output fed back into System One or a host as instructions |
| TH-6 | prompt injection inside traces steering the optimizer |
| TH-7 | trace files readable by other local users |
| TH-8 | encoded secrets (base64, URL-encoded, split) bypass patterns |

## Mitigations

| Threat | Mitigation | Requirement |
|---|---|---|
| TH-1, TH-8 | redaction on ingest; post-scan must be clean; canary corpus with encoded forms | REQ-003, REQ-004 |
| TH-2 | email and home-path classes | REQ-003 |
| TH-3 | default `none`; consent only by preview digest; no expiry (OD-3), `status` shows level, `consentedAt` and sources | REQ-001, REQ-002 |
| TH-4 | sweep at store open and on command; purge; tests with clock injection | REQ-005 |
| TH-5 | read-only System One access; no output path into System One | REQ-007 |
| TH-6 | traces are data; SPEC-072 optimizer treats them as untrusted; promotion is human (SPEC-073) | REQ-006 |
| TH-7 | owner-only modes, no symlinks (SPEC-070 F1) | REQ-005 |

## Residual risks

- Pattern-based redaction cannot catch every secret shape or every piece of
  personal data (for example names in free text); consent `redacted` accepts
  this residual risk explicitly in the preview text.
- Host transcripts may change format; unknown fields become losses, not content.
- Base64 detection is heuristic (length and alphabet thresholds); false
  negatives remain possible below the threshold.
- Purge cannot reach copies the owner made outside the store.
