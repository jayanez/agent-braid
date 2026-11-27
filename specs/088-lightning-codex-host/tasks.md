# SPEC-088: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`python3 scripts/validate_change.py --base develop --profile quick`. No task changes
`REQUIRED_HOSTS`, adds Codex as an optimizer host, edits a closed specification or a
SPEC-069 to SPEC-073 driver, or opens the export terms gate. This first PR is
documentation only; the tasks from T002 on wait for owner approval (T001) and for
SPEC-087's registry code.

## Phase P0 — review and baseline

- [ ] T001 (REQ-001 / SC-001): Owner review of spec and plan, including OD-5 (held-out guard) and the proposed SPEC-087 amendments.
  Dependencies: none. Target files: none. Verification: procedure_001. Planned
  evidence: `evidence/t001-owner-review.md`; obtained: none.
- [ ] T002 (REQ-005 / SC-005 REQ-012 / SC-012): Record the differential baseline of the Lightning host path from `develop` after SPEC-087's registry code.
  Regenerate the host-site scan of the plan's table, the output bytes of `lightning init`
  preview, `run --dry-run`, `run --fake-hosts`, `status`, `report`, the config, schema and
  export-terms refusals, the default-config digest and the SHA-256 of every committed
  Lightning fixture and record; confirm the consent check carries no host literal.
  Requires T001 and SPEC-087 T007. Target files: `specs/088-lightning-codex-host/evidence/`.
  Verification: procedure_005, procedure_012. Planned evidence: `evidence/t002-baseline.json`;
  obtained: none.

## Phase P1 — observation (no quota without the owner's yes)

- [ ] T003 (REQ-007 / SC-007 REQ-009 / SC-009): Observe the Codex route, credential carrier, model identity and stream shapes.
  Read recorded Codex streams (the SPEC-069 T010 Codex evidence) and the existing Codex
  observer contract; state what, if anything, the stream or the app-server account read
  reports as a credential source, which carrier a disposable profile needs, and where the
  model identity comes from. Any new real Codex invocation needs the owner's explicit
  yes first and runs on the subscription route with no provider key. No credential file is
  read. The outcome is one of: a reported source (value named), an observed route with
  review, or none (Codex stays a declared limit). Names the Codex build. Requires T001.
  Target files: `specs/088-lightning-codex-host/evidence/`. Verification: procedure_007,
  procedure_009. Planned evidence: `evidence/t003-codex-observation.json`; obtained: none.

## Phase P2 — registry, config, schema

- [ ] T004 (REQ-002 / SC-002 REQ-003 / SC-003 REQ-004 / SC-004): Edit the registry capabilities.
  Add `codex` to `lightning-run` (appended), add `lightning-optimizer` with `claude-code`
  only, update the recorded membership table and the registry tests. Requires T002.
  Target files: `agent_braid/host_registry.py`, `tests/test_host_registry.py`.
  Verification: procedure_002, procedure_003, procedure_004. Planned evidence:
  `evidence/t004.json`; obtained: none.
- [ ] T005 (REQ-004 / SC-004 REQ-005 / SC-005 REQ-006 / SC-006 REQ-013 / SC-013): Config, schema and export-terms acceptance.
  `rollout.hosts` options from `lightning-run` with the fixed default
  `['claude-code', 'opencode']` pinned by a subset test; `optimizer.host` and
  `--optimizer-host` from `lightning-optimizer`; schema host enums and the terms-record
  host check from `lightning-run`; version strings unchanged; the terms gate stays closed.
  Requires T004. Target files: `agent_braid/lightning_config.py`,
  `agent_braid/lightning_cli.py`, `agent_braid/lightning_schema.py`,
  `agent_braid/lightning_export.py`, their tests. Verification: procedure_004,
  procedure_005, procedure_006, procedure_013. Planned evidence: `evidence/t005.json`;
  obtained: none.

## Phase P3 — runner and parser

- [ ] T006 (REQ-003 / SC-003 REQ-007 / SC-007 REQ-008 / SC-008 REQ-010 / SC-010 REQ-014 / SC-014): Runner tables, route verdict, declared limit, fake host and held-out guard.
  `CREDENTIALS`, fake-binary, binary, accepted key-source and declared-limit tables keyed
  by `lightning-run`; `codex` entries from T003 (none accepted until it records a
  source); the `opencode` branches become table lookups with the same results; add
  `tests/fixtures/lightning-fake-hosts/codex`; refuse a `codex` host on `HELDOUT` and
  `TEST_SETS` prompt sets before launch; key-set tests. Requires T003 and T005. Target
  files: `agent_braid/lightning_runner.py`, `tests/fixtures/lightning-fake-hosts/codex`,
  `tests/test_lightning_codex_host.py`. Verification: procedure_003, procedure_007,
  procedure_008, procedure_010, procedure_014. Planned evidence: `evidence/t006.json`;
  obtained: none.
- [ ] T007 (REQ-009 / SC-009 REQ-003 / SC-003): Verify `parse_codex`, the tool prefix and the tool classes on recorded Codex streams.
  Fix only a mismatch the recorded streams show; name the Codex build; record a missing
  model as unobserved. Requires T003. Target files: `agent_braid/lightning_hosts.py`,
  `tests/test_lightning_codex_host.py`. Verification: procedure_003, procedure_009.
  Planned evidence: `evidence/t007.json`; obtained: none.
- [ ] T008 (REQ-010 / SC-010 REQ-011 / SC-011 REQ-015 / SC-015): Pipeline test with fake hosts and the verdict-unchanged check.
  `lightning run --fake-hosts` over `claude-code`, `opencode` and `codex`; `report` shows
  Codex rows; `h1_outcome`, the SPEC-049 pair and the promotion inputs equal those from
  the `claude-code` rows alone; `--dry-run` keeps `executionAuthorization` false. Requires
  T006 and T007. Target files: `tests/test_lightning_codex_host.py`. Verification:
  procedure_010, procedure_011, procedure_015. Planned evidence: `evidence/t008.json`;
  obtained: none.

## Phase P4 — documentation, closure checks, evidence

- [ ] T009 (REQ-017 / SC-017): Update `docs/tooling/LIGHTNING.md`.
  State Codex as a rollout host, non-binding, `route-unverified` until evidence, optimizer
  on Claude Code only, held-out guard; no claim of a Codex result. Requires T008. Target
  files: `docs/tooling/LIGHTNING.md`. Verification: procedure_017. Planned evidence:
  `evidence/t009.json`; obtained: none.
- [ ] T010 (REQ-005 / SC-005 REQ-016 / SC-016 REQ-012 / SC-012): Re-run the differential record and check the change scope.
  Rerun T002's recording; identical bytes and sets for `claude-code` and `opencode`
  apart from accepted-host text; list the changed paths; run the full existing suites and
  `quick`. A difference is reported, not tuned away. Requires T008 and T009. Target
  files: `specs/088-lightning-codex-host/evidence/`. Verification: procedure_005,
  procedure_012, procedure_016. Planned evidence: `evidence/t010-after.json`; obtained:
  none.

## Phase P5 — first real Codex rollout (owner-gated)

- [ ] T011 (REQ-015 / SC-015 REQ-007 / SC-007 REQ-017 / SC-017): Owner decision and, if yes, one bounded Codex rollout on the development prompt set.
  The owner authorizes or declines the real run in a dated record, after reading T003 and
  T010. If authorized: subscription route only, no provider key, development prompt set
  only, one run, results recorded with their route verdict; a `route-unverified` outcome
  is a valid result and ends as a declared limit. No claim about Codex validity is made.
  Requires T010 and the owner's yes. Target files: `specs/088-lightning-codex-host/evidence/`.
  Verification: procedure_015, procedure_007, procedure_017. Planned evidence:
  `evidence/t011-owner-decision.md`; obtained: none.
