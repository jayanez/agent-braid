# Implementation plan: SPEC-091 — Invocation gate (gate B)

## Technical context and scope

- New module `agent_braid/lightning_gate_b.py`: gate B analysis.
- New module `scripts/spec091_build_items.py`: labelled item sets and factorial cells.
- New module `scripts/spec091_freeze.py`: freezes and checks; new document `specs/091-invocation-gate/labelling-rubric.md`.
- New module `agent_braid/lightning_levers.py`: wraps the server definition at laboratory build time
  (`alwaysLoad` in `_meta`, server instructions, description overlay) without editing it.
- Changed: `scripts/spec069_native_runs.py` (a new gate B profile; existing profiles keep `Read`, `Grep`,
  `Glob` and `Bash` disabled), `agent_braid/plugin_mcp.py` (lever builds behind laboratory flags), the
  plugin under `integrations/agent-braid/plugin/` (hook and command arms),
  `agent_braid/lightning_config.py` and `agent_braid/lightning_resources.py` (target kinds).
- Reused: SPEC-090 bounds, selection, drift controls, journal and tripwire; the SPEC-071 runner.
- Unchanged: the SPEC-069 scorer and sets, SPEC-078 and SPEC-079 records (REQ-023).
- Read only: `agent_braid/tooling_mcp.py` and the canonical
  `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md` MUST stay byte-identical while
  `specs/079-kind-choice-tool-fix/prompts/FREEZE-v4.json` binds them (`scripts/spec079_freeze.py` BOUND,
  checked by `tests/test_spec079_boundaries.py`); SPEC-079 T009 and T010 are open (REQ-023, REQ-043).

## Constitution check before research

Clause zero and Articles 9, 12, 13, 14, 19, 20, 21, 23. Obligations mapped: labels and protocols frozen
before observation (REQ-002, REQ-013, REQ-014); evidence bounded to the laboratory, host and model;
negative results recorded (T017); EUR 0 (ADR 0021); Lightning boundary (ADR 0039); containment (ADR 0035);
the tool contract (ADR 0038) changes only after OD-10. No MUST conflict found. A hook that adds context to
every prompt is a new authority and privacy surface; it stays laboratory-only (OD-11, REQ-025).

## Research, assumptions and alternatives

See [research.md](research.md). Items are authored synthetic prompts over the SPEC-069 fixture workspace,
labelled by the OD-2 procedure; no user or third-party data. Labels are human proxy labels of product
intent; the observed outcome is whether `analyze-work` was called.

## Design

1. **Items (REQ-002, REQ-003, REQ-019).** A rubric states each label's test: necessary when the needed fact
   is absent from the prompt, beneficial when a verified, auditable artifact is what the request asks for,
   unnecessary otherwise. Two independent labels and adjudication per OD-2; the label record is frozen by
   hash and versioned.
2. **Laboratory (REQ-004, REQ-022).** A new profile enables the OD-5 tools and installs the pinned skills;
   every other tool stays disabled and the SPEC-071 disposable profile rules hold.
3. **Levers (REQ-005 to REQ-008).** Each lever is a build flag producing a distinct digest; compared arms
   share the pinned plugin commit, host and model and differ only in lever flags. `alwaysLoad` and server
   instructions change the MCP surface through `agent_braid/lightning_levers.py`, which wraps the server
   definition at laboratory build time and leaves `agent_braid/tooling_mcp.py` unchanged; the skill description
   (`integrations/agent-braid/skills/agent-braid-analyze/SKILL.md` front matter) leads with the use case
   within its cap; the hook prints only its frozen factual string; the explicit command calls `analyze-work`.
4. **Target kinds (REQ-009, REQ-010).** `target.kind` adds the OD-14 kinds. `lightning_resources` extracts
   the target field (front-matter `description`, or the server-instructions string), mutates only it, and
   re-assembles with the rest hashed; the `skill` path keeps its current byte behaviour.
5. **Pilots (REQ-011, REQ-012).** The gate B noise pilot runs A/A pairs and two candidate arms on fresh
   development prompts that do not name the product and writes the SPEC-090 sizing input for gate B; gate
   A has its own pilot (SPEC-090 REQ-032). The development factorial crosses three of the seven v3/v4
   differences over fresh prompts at OD-6; it does not isolate the v3 to v4 change.
6. **2×2 factorial (REQ-013).** Description (current, use-case-first) × hook (absent, present), on one
   pinned build per cell, within-item design, seeded interleaved blocks, OD-7 recall-labelled plus OD-8
   `tool-unnecessary` items per cell (rollouts = items × 3); the item is the unit (OD-17); named contrasts
   and candidate analyses in evaluation-protocol.md, one picked by T007; Holm over the two recall main
   effects (OD-19), false positives as an unadjusted noninferiority condition (REQ-037); the interaction is
   tested for equivalence within ±η (OD-18) by TOST.
6a. **Description overlay and decisive cell (REQ-043, REQ-044).** The use-case-first description is applied as
   an overlay when a lever build is assembled; the canonical SKILL.md stays byte-identical. T011 names the
   one decisive 2×2 cell for REQ-014.
6b. **Real-run order.** Real-run order, the same in ADR 0046, SPEC-090 and SPEC-091: the gate A noise pilot (SPEC-090 T020) and,
   independently and in either order, the gate B noise pilot (SPEC-091 T008) and development factorial
   (SPEC-091 T009); then lever screening (SPEC-091 T018) and the 2×2 factorial (SPEC-091 T012); then gate B
   selection (SPEC-091 T019) only when SPEC-091 OD-20 requires it, and the same-build gate A run
   (SPEC-091 T023) whenever the arm under test changes the description, server instructions, `_meta` or the
   hook; then SPEC-091 T021 and T015. SPEC-090 T022 and T017 depend only on SPEC-090 T016 and may run at any
   point after it. SPEC-091 T016 may run at any point after its own freeze. Each run MUST be behind its own
   freeze and owner yes record (SPEC-090 REQ-017, SPEC-090 REQ-045, SPEC-091 REQ-045).

6c. **Lever screening (REQ-033).** `alwaysLoad` and server instructions are screened against the shipped
   build in T018 before the 2×2 factorial, so every built lever is measured.
6d. **Verdict (REQ-034).** Conjunctive, so a false `met` stays at or below α by the intersection–union
   principle; precedence as SPEC-090 REQ-038.
6e. **Freezes and stops (REQ-035, REQ-036).** Each development pilot has its own freeze; stops follow
   SPEC-090 REQ-037.
7. **Held-out (REQ-014, REQ-015).** Built only after the factorial meets the paired OD-9 criterion in the
   decisive cell (REQ-044); its pool shares no item, fingerprint or normalized 8-word window with any pilot,
   screening, 2×2, selection or audit item, nor with the SPEC-069, v2, v3 or v4 sets; the arm is OD-20;
   Gate 0 (T021) compares the twin's rollout-level call rate with that of the OD-20 arm on recall-labelled
   items in T012, minus the OD-22 margin. Gate B has no reserve: a rollout with an instrument event is
   excluded and re-run once (REQ-039).
8. **Data model and evolution.** The label record, the item set, the lever catalogue and the gate B report
   each carry a `schema` version string; a relabel or a new lever adds a version and never rewrites a
   measured one (REQ-027); a reader rejects an unknown version. The `target.kind` enumeration grows by
   explicit values only (REQ-009); existing configuration files need no migration (REQ-029).
9. **Dependency failure.** If a SPEC-090 dependency (bounds, selection, drift controls) is unavailable, the
   dependent task stops and no real run starts. If host documentation no longer describes a lever, or the
   lever fails on the pinned host, its arm is recorded as `unavailable` and dropped from the comparison,
   not replaced by a guess. If the hook arm is unavailable (its context never appears, REQ-039), the 2×2
   factorial reduces to its preregistered description-only paired comparison and REQ-014 uses that, so
   gate B can still run.
10. **Same-build certification and selection (REQ-038, REQ-041, REQ-042).** A build that changes the
   description, server instructions, `_meta` or the hook needs gate B met and, on that same build, gate A
   met or SPEC-049 noninferiority on a second, freshly authored gate A split (T023). Selection (T019) runs
   only when the decisive cell (REQ-044) misses OD-3; its incumbent is that cell; the winner and the
   incumbent are each scored once on the labelled gate B audit set (T022) and the SPEC-090 gate A audit
   set, the paired difference is reported with an exact interval, and the audit result does not change the
   selection.
12. **Owner yes (REQ-045).** The runner refuses a SPEC-091 run without a dated line in
   `specs/091-invocation-gate/evidence/owner-yes.md` naming the specification, task, run and frozen
   protocol hash, or whose protocol lacks the hash of the T007 simulation record.
11. **Other hosts (REQ-025).** The plugin is shared by codex, claude and opencode
   (`integrations/agent-braid/hosts.json`), and T004 edits shared files; a lever ships scoped to
   claude-code only, or after a non-regression measurement on each other host, which SPEC-089 (a skeleton)
   does not yet specify.

## Validation strategy

Generated from `assurance.json`; each test file is listed in the Files of the task that owns it.

| Task | REQ | SC | Test file |
|---|---|---|---|
| T002 | REQ-002, REQ-003, REQ-019, REQ-027, REQ-028, REQ-040 | SC-002, SC-003, SC-020, SC-028, SC-029, SC-042, SC-047 | `tests/test_spec091_items.py` |
| T003 | REQ-004, REQ-021, REQ-022, REQ-031, REQ-045 | SC-004, SC-022, SC-023, SC-032, SC-056 | `tests/test_spec091_lab.py`, `tests/test_spec091_boundaries.py` |
| T004 | REQ-005, REQ-006, REQ-024, REQ-032, REQ-043 | SC-005, SC-007, SC-025, SC-033, SC-045 | `tests/test_spec091_levers.py`, `tests/test_spec091_boundaries.py` |
| T005 | REQ-005, REQ-007, REQ-008 | SC-006, SC-008, SC-009 | `tests/test_spec091_levers.py` |
| T006 | REQ-009, REQ-010, REQ-029 | SC-010, SC-011, SC-030 | `tests/test_lightning_resources.py` |
| T007 | REQ-018 | SC-019 | `tests/test_lightning_sim.py` |
| T008 | REQ-012, REQ-035 | SC-013, SC-037 | `tests/test_spec091_pilots.py` |
| T009 | REQ-011, REQ-035 | SC-012 | `tests/test_spec091_pilots.py` |
| T010 | REQ-001, REQ-013, REQ-017, REQ-026, REQ-034, REQ-037, REQ-039 | SC-001, SC-018, SC-027, SC-035, SC-036, SC-039, SC-041, SC-049 | `tests/test_lightning_gate_b.py` |
| T011 | REQ-013, REQ-023, REQ-036, REQ-044 | SC-014, SC-024, SC-038, SC-046, SC-048 | `tests/test_spec091_pilots.py`, `tests/test_spec091_boundaries.py` |
| T013 | REQ-009, REQ-020 | SC-021 | `tests/test_lightning_resources.py` |
| T014 | REQ-014, REQ-015, REQ-035 | SC-015, SC-016, SC-050, SC-051, SC-052, SC-054 | `tests/test_lightning_gate_b.py`, `tests/test_spec091_boundaries.py` |
| T016 | REQ-016, REQ-030, REQ-035 | SC-017, SC-031 | `tests/test_lightning_gate_b.py` |
| T017 | REQ-025 | SC-026, SC-053 | `tests/test_spec091_boundaries.py` |
| T018 | REQ-033, REQ-035 | SC-034 | `tests/test_spec091_pilots.py` |
| T019 | REQ-041 | SC-043, SC-055 | `tests/test_lightning_gate_b.py` |
| T022 | REQ-042 | SC-044 | `tests/test_spec091_items.py` |
| T023 | REQ-038 | SC-040 | `tests/test_spec091_boundaries.py` |

Labels are human proxy labels; disagreements are recorded verbatim and reported with agreement. Missing
results count as non-calls and are reported separately; a rollout with an instrument event is excluded and
re-run once (REQ-039). Calibration is not claimed.

## Constitution check after design

No execution authority, no paid route, no new dependency, frozen paths untouched, labels and protocols
precede observation. The hook stays laboratory-only pending OD-11. No blocker.

## Human review and unresolved decisions

OD-1 to OD-28 are open (spec.md). Owner yes required for T008, T009, T018, T012, T019, T023, T021, T015
and T016. SPEC-079 T009
is not decided here.
