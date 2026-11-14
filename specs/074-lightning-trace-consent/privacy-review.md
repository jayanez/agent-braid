# SPEC-074: Privacy review

Draft for owner review; not an approval.

## Data inventory

| Data | Source | Contains | Stored where | Retention |
|---|---|---|---|---|
| rollout events | SPEC-071 runner | prompts, responses, tool calls, rewards | plugin home `lightning/runs/<id>/` (owner-only) | 30 days default, ≤ 90 |
| host transcripts | Claude Code, Codex, OpenCode local logs, read only when `host-transcript` is in `traces.sources` (OD-1) | user prompts, code, paths, possibly secrets | read in place, never copied unredacted | host-controlled |
| Loom stream | Loom viewer events | activity metadata, labels | read in place | Loom-controlled |
| System One episodes | shadow store | prompts and advisory answers | read in place, read-only | 30 days (SPEC-066) |
| triplets/messages | adapter output | redacted text, rewards | run directory | same as rollouts |
| email salt | per run (OD-2) | random salt for `[REDACTED:email:<8-hex>]` tags | owner-only run directory | deleted with the run by purge or sweep |
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
| TH-2 | email and home-path classes; email tags salted per run, unlinkable across runs (OD-2) | REQ-003 |
| TH-3 | default `none`; consent only by preview digest; no expiry (OD-3), `status` shows level, `consentedAt` and sources | REQ-001, REQ-002 |
| TH-4 | sweep on `lightning sweep`, `purge --expired` and every content append for its run; purge; tests with clock injection | REQ-005 |
| TH-5 | read-only System One access; no output path into System One | REQ-007 |
| TH-6 | traces are data; SPEC-072 optimizer treats them as untrusted; promotion is human (SPEC-073) | REQ-006 |
| TH-7 | owner-only modes, no symlinks (SPEC-070 F1) | REQ-005 |
| TH-2 | source ids (attempt, strand, operation, episode) are free text, so outputs carry salted HMAC pseudonyms, one domain per kind; refusals name no source value and carry no chained cause | REQ-006 |

## Residual risks

- Pattern-based redaction cannot catch every secret shape or every piece of
  personal data (for example names in free text); consent `redacted` accepts
  this residual risk explicitly in the preview text.
- Host transcripts may change format; unknown fields become losses, not content.
- Base64 detection is heuristic (length and alphabet thresholds); false
  negatives remain possible below the threshold.
- Purge cannot reach copies the owner made outside the store.
- Retention is enforced when a command or a content append runs (A1); content
  past retention stays on disk until the next one.
- Pseudonyms are keyed HMAC names, not anonymization: anyone holding the salt
  (the run salt for rollout attempts, the caller's salt otherwise) can test a
  guessed id against a name. The rollout `rolloutId` is still the SPEC-070
  event's own id (A7).

## Convergence findings (T011)

Read-only analysis of spec, plan, tasks, contracts and obtained evidence at
convergence (2026-11-14; A5–A8 added at the re-convergence after #1368 and #1376, same day). None blocks a requirement; each is stated so the
owner's review sees it.

| ID | Finding | Effect |
|---|---|---|
| A1 | The draft mitigation for TH-4 said the sweep runs at store open; the implementation sweeps on `lightning sweep`, `purge --expired` and each content append for its own run (procedure_005); reading a run does not sweep. | Mitigation text corrected; residual risk added above. REQ-005 does not fix when the sweep runs. |
| A2 | REQ-006 names the host observers; T008 reads host transcripts through `trace_adapter`, which admits synthetic traces only, so a real host transcript cannot be read yet even with `host-transcript` listed (OD-1). | Pending outside the requirements: a real-source admission is future work; no real transcript content is collected today. |
| A3 | T010 found that no BL.4 path records ADR 0025 telemetry at all (procedure_008), which is stronger than content-free and matches the "unchanged" telemetry row. | A future telemetry event for Lightning would fail the T010 test and needs its own review. |
| A4 | The REQ-008 `executionAuthorization: false` check covers successful BL.4 CLI outputs; refusals print text to stderr, and `lightning run` / `report` belong to SPEC-071/072 and their boundary tests. | Scope of the claim stated in procedure_008 limits. |
| A5 | Review of #1368 (merged after the first convergence): the Loom readers emitted raw strand ids, which are free text. | Fixed in #1368: every reference at a `view_loom` schema position is named `strand-<hmac16>` from one map per stream, shared by triplets and messages; other fields keep their values; colliding names refuse the stream (procedure_006). |
| A6 | Review of #1376: rollout attempt ids and System One episode ids were emitted raw; two refusals interpolated the attempt id or the parser message, and refusals chained the source exception, whose text can hold a path or id. | Fixed in #1376: `attempt-` (run salt) and `episode-` pseudonyms; fixed refusal texts raised `from None`; store and short-salt errors become adapter refusals (procedure_006, procedure_008). |
| A7 | Transcript turn names had no HMAC domain, so an e-mail used as an attempt id gave a `turn-` name sharing the redactor's e-mail tag hex. | Fixed in #1376: each kind (`turn`, `strand`, `attempt`, `episode`) has its own domain, pinned by one known name per kind. `turn-` names changed; nothing consumes them. The `rolloutId` of rollout records is not pseudonymized (residual risk above). |
| A8 | The first convergence (#1372, 2026-11-14) predates #1368 and #1376. | This convergence re-reads spec, contracts, validation plan and the recaptured evidence with both fixes; `contracts/triplet.md` now names the pseudonym kinds, their salts, the Loom message renaming and the refusal rules. |
