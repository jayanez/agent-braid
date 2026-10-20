# Real backlog coverage prototype

Status: RF-T10 / proposed SPEC-045/T017 development increment, human and independent
review pending. REQ-CI-009 / SC-CI-009 retain their supplement identities. This
document does not amend the historical synthetic assurance or close the task.
Constitution Articles 7, 13, 14, 19 and 20 require inspectable boundaries and useful
negative results. SPEC-028/029/031/032/033 retain their source, review, native and
promotion gates. The current implementation is a research helper, with no CLI,
MCP, runtime or forecasting integration.

## Version and meaning

`research.owned_work_coverage.assess_backlog` returns
`agent-braid-backlog-coverage/v1`. It accepts a list of exact metadata objects:
`taskId`, `attemptId`, `originalPaths`, `presentedPaths`, `operationCount` and
`workflowStatus`. IDs are bounded ASCII identifiers, paths are unique ordinary
relative strings and counts are nonnegative integers or null. Bounds are 1,000
attempts, 256 paths per list, 512 UTF-8 bytes per path and 1 MiB canonical input.
The helper does no filesystem, subprocess, clock, model, collector or network I/O.

This is a necessary-condition prefilter of the pinned typed-v1 domain:
`[a-z0-9][a-z0-9.-]*\.txt`, one to eight files, two to four operations. Its
`verifierSHA256` identifies the referenced source, not a live verification result.
The caller must bind the actual source hash; a test detects reference drift.
Original-path provenance and population completeness remain caller obligations.
Matching declarations cannot detect an undisclosed false original path.

| Metadata result | Meaning |
|---|---|
| refused | Presented paths differ from original paths, including omitted paths |
| unsupported | A known path/file-count/operation-count limit excludes the task |
| unknown | Necessary limits did not exclude it; the full verifier was not run |
| supported | Never produced by this helper |

No path is normalized, renamed, copied or truncated to enter typed-v1. Reordering
the same path set is harmless. A null operation count stays unavailable. Grammar,
operation identities, source roots/rights, fixture marker, goals, observation
completeness, resource budgets and native preparation remain unverified even for
matching `.txt` metadata. Unsupported metadata does not prevent software edits
under the owner's independent development authorization.

Every supplied retry and workflow state remains in the denominator: registered,
completed, refused, cancelled, error, missing, abandoned and not-selected. A
workflow state is bookkeeping, never a predictor or an independently established
label. Duplicate attempt IDs or malformed/over-budget batches fail atomically;
the caller must retain that input and failure under its own authorized records.
The helper does not provide an append-only all-attempt registry.

`supportedFraction` is observed supported decisions divided by supplied attempts
(always zero for this prefilter); an empty population returns null. Unknown is
not supported or semantically incorrect. The input digest binds exact supplied
metadata, including workflow states; it is not consent, anonymization, immutable
prediction-time lineage or proof that all attempts were supplied. No success,
productivity, forecast error, interval coverage or calibration metric follows.

## Validation and evidence

Run `python -m unittest tests.test_owned_work_coverage -v` in Python 3.12+.
The tests cover ordinary `.py`/`.md`/nested paths, path laundering and omission,
unknown compatible metadata, file/count bounds, retries and all terminal states,
empty populations, duplicate identity, malformed inputs, size caps and input
binding. These are software controls, not independent workload observations.
The actual task registration, raw logs, mutation controls and source/hash
manifest belong to the separate local engineering handoff. No new source ledger
or training corpus is created by this prototype. Existing v1 source stays pinned.

## Proposed domain extension after the negative coverage result

Candidate identity: `owned-repo-lf-patch-v2-draft`; IR/observation identities:
`owned-repo-lf-program-v2-draft` / `owned-repo-path-blob-v2-draft`. None is registered
or activated. This is a new finite text-patch domain, not Python semantic analysis.
The minimum proposed changes are explicit owner-bound repository admission in
place of fixture-only ownership, ordinary nested relative `.py`/`.md` paths and
LF blank lines. Retain A/M regular-file effects, 2–4 operations, dependency and
offered-plan checks, finite byte/line/hunk budgets, exact preimages/postimages,
whole-goal verification and advisory-only output. Do not relax budgets to force
this task to fit; unsupported sizes remain counted.

Before implementation/admission, specify canonical path/alias and symlink/link
rules, ignored/untracked handling, source permissions, content minimization and
new verifier/registry/source pins. Add controls for traversal, case aliases,
symlinks, binary/NUL/CRLF input, blank lines, nested imports, ambiguous anchors,
stale preimages, oversized additions, goal mismatch and interrupted cleanup.
Cross-check bounded patch outcomes with isolated Git and retain discrepancies.
Code correctness still needs the task's own tests; equal blobs are insufficient.

Migration is opt-in with new identities and explicit refusal of cross-version
receipts. Keep all v1 verifiers, policies, evidence and refusal tests unchanged.
No conversion of v1 fixtures into real-work evidence is permitted. Domain,
source/privacy, registry, cost and independent review must be obtained before
an evaluation lot; human labels and operational acceptance remain separate.
