# Implementation plan: SPEC-091 — Invocation gate (gate B)

## Technical context and scope

- New module `agent_braid/lightning_gate_b.py`: gate B analysis.
- New module `scripts/spec091_build_items.py`: labelled item sets and factorial cells.
- New module `scripts/spec091_freeze.py`: freezes and checks; new document `specs/091-invocation-gate/labelling-rubric.md`.
- Changed: `scripts/spec069_native_runs.py` (a new gate B profile; existing profiles keep `Read`, `Grep`,
  `Glob` and `Bash` disabled), `agent_braid/tooling_mcp.py` and `agent_braid/plugin_mcp.py` (lever builds
  behind laboratory flags), the plugin under `integrations/agent-braid/plugin/` (hook and command arms),
  `agent_braid/lightning_config.py` and `agent_braid/lightning_resources.py` (target kinds).
- Reused: SPEC-090 bounds, selection, drift controls, journal and tripwire; the SPEC-071 runner.
- Unchanged: the SPEC-069 scorer and sets, SPEC-078 and SPEC-079 records (REQ-023).

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
3. **Levers (REQ-005 to REQ-008).** Each lever is a build flag producing a distinct digest. `alwaysLoad`
   and server instructions change the MCP surface; the skill description leads with the use case within
   its cap; the hook prints only its frozen factual string; the explicit command calls `analyze-work`.
4. **Target kinds (REQ-009, REQ-010).** `target.kind` adds the OD-14 kinds. `lightning_resources` extracts
   the target field (front-matter `description`, or the server-instructions string), mutates only it, and
   re-assembles with the rest hashed; the `skill` path keeps its current byte behaviour.
5. **Pilots (REQ-011, REQ-012).** The noise pilot runs A/A pairs and two candidate arms on fresh
   development prompts and writes the SPEC-090 sizing input. The development factorial crosses the three
   prompt factors over fresh prompts at OD-6.
6. **2×2 factorial (REQ-013).** Description (current, use-case-first) × hook (absent, present), on one
   pinned build per cell, seeded interleaved blocks, OD-7 rollouts per cell and metric; logistic or exact
   per-cell comparison chosen by T007 simulation.
7. **Held-out (REQ-014, REQ-015).** Built only after the factorial meets OD-9; Gate 0 includes the tripwire.
8. **Data model and evolution.** The label record, the item set, the lever catalogue and the gate B report
   each carry a `schema` version string; a relabel or a new lever adds a version and never rewrites a
   measured one (REQ-027); a reader rejects an unknown version. The `target.kind` enumeration grows by
   explicit values only (REQ-009); existing configuration files need no migration (REQ-029).
9. **Dependency failure.** If a SPEC-090 dependency (bounds, selection, drift controls) is unavailable, the
   dependent task stops and no real run starts. If host documentation no longer describes a lever, or the
   lever fails on the pinned host, its arm is recorded as `unavailable` and dropped from the comparison,
   not replaced by a guess.

## Validation strategy

| REQ | SC | Test | Planned evidence |
|---|---|---|---|
| REQ-001, REQ-017, REQ-026 | SC-001, SC-018, SC-027 | `tests/test_lightning_gate_b.py` | T010 |
| REQ-002, REQ-003, REQ-019, REQ-027, REQ-028 | SC-002, SC-003, SC-020, SC-028, SC-029 | `tests/test_spec091_items.py` | T002 |
| REQ-004, REQ-021, REQ-022, REQ-031 | SC-004, SC-022, SC-023, SC-032 | `tests/test_spec091_lab.py`, `tests/test_spec091_boundaries.py` | T003 |
| REQ-005 to REQ-008, REQ-024, REQ-032 | SC-005 to SC-009, SC-025, SC-033 | `tests/test_spec091_levers.py` | T004, T005 |
| REQ-009, REQ-010, REQ-020, REQ-029 | SC-010, SC-011, SC-021, SC-030 | `tests/test_lightning_resources.py` | T006, T013 |
| REQ-011, REQ-012, REQ-013 | SC-012 to SC-014 | `tests/test_spec091_pilots.py` | T008, T009, T011 |
| REQ-014, REQ-015, REQ-016, REQ-030 | SC-015 to SC-017, SC-031 | `tests/test_lightning_gate_b.py` | T014, T016 |
| REQ-018 | SC-019 | `tests/test_lightning_sim.py` | T007 |
| REQ-023, REQ-025 | SC-024, SC-026 | `tests/test_spec091_boundaries.py` | T011, T017 |

Labels are human proxy labels; disagreements are recorded verbatim and reported with agreement. Missing
results count as non-calls and are reported separately. Calibration is not claimed.

## Constitution check after design

No execution authority, no paid route, no new dependency, frozen paths untouched, labels and protocols
precede observation. The hook stays laboratory-only pending OD-11. No blocker.

## Human review and unresolved decisions

OD-1 to OD-16 are open (spec.md). Owner yes required for T008, T009, T012, T015 and T016. SPEC-079 T009
is not decided here.
