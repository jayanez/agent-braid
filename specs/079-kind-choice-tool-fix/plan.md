# Implementation plan: SPEC-079 — Tool-level kind-choice fix (BL.2c)

## Technical context and scope

- Tool surface: `agent_braid/tooling_mcp.py` (`_analyze_work`, `_ANALYZE_WORK_SCHEMA_HELP`,
  `_tool_definitions`); `agent_braid/units.py` supplies `construct` and stays unchanged.
- Evaluation: new builder `scripts/spec079_build_v4.py` reusing the SPEC-078 fact generator and
  expectation rule (`scripts/spec078_build_set.py`) and Gate 0 (`scripts/spec078_gate0.py`) by import;
  analysis by `agent_braid/lightning_heldout_v2.analyse` (OD-1). Runner: SPEC-071 on `claude-code`.
- Artifacts live in `specs/079-kind-choice-tool-fix/` (`prompts/v4-test.json`,
  `evaluation-protocol.md`, `prompts/FREEZE-v4.json`, `evidence/`).
- Out of scope: everything listed in spec.md "Out of scope"; frozen SPEC-078 files are read only.

## Constitution check before research

Clause zero and Articles 9, 12, 13, 14, 19, 20, 21, 23 (as SPEC-078). Obligations mapped:
bounded, read-only analysis with no execution authority (refusal keeps
`executionAuthorization: false`); evidence limited to its domain (one host, model, split);
preregistration before observation (freeze before rollout); negative results recorded; EUR 0 (ADR 0021);
Lightning boundary (ADR 0039: no promotion, no training). No MUST conflict found. SHOULD deviation:
none. The `units` behaviour change alters SPEC-069 REQ-006 observable output for disjoint input; it is
recorded as a versioned compatibility change (REQ-005), not an override of a constitutional obligation.

## Research, assumptions and alternatives

See [research.md](research.md). Data source: prompts are authored synthetic tasks over the existing
SPEC-069 fixture workspace; no user, telemetry or third-party data, so no consent gate applies. Yield is
fixed by construction (100 prompts); a builder that cannot reach 100 valid cases under the leakage
checks is a feasibility failure reported as such, not a reason to relax the checks.

## Design and compatibility

1. **Disjointness test (REQ-001).** After `units.construct`, compute for every pair of constructed
   records: shared `write`/`delete` resource, write/read overlap, or a dependency edge. If no pair has
   any of these, raise `ToolingError(code="units-cannot-answer-independence")` carrying a message
   (<= 400 chars) and `result.constructedRequest` (coverage partial). Any overlapping or dependent pair,
   or a single unit, takes the existing path unchanged. Validation refusals of `units.validate` stay first.
2. **Refusal envelope (REQ-002).** Reuse the existing refused envelope (`status: refused`,
   `executionAuthorization: false`); the constructed envelope is attached under `result` only.
3. **Descriptions (REQ-003, REQ-004).** Replace `_ANALYZE_WORK_SCHEMA_HELP` with text of the form:
   "Parallel/overlap questions: kind aim. units cannot report independence and is refused for
   disjoint work. digest fields: any sha256:<64 lowercase hex> label you choose for the definition and
   input, e.g. sha256 of the task text; one evidence item; coverage complete if every touched file is
   named. git: branches, distinct attemptIds. Skill agent-braid-analyze." Add an `analyze` description:
   "takes a plan-level request; it does not compare proposed work for parallelism or overlap — use
   analyze-work." Both checked against the D12 cap by a frozen-text test. `description-only` delivery
   gets the same `units` sentence.
4. **Compatibility (REQ-005).** Release record and `docs/tooling/NATIVE_PLUGINS.md` entry; shipped only in the alpha after
   the v4 result (OD-D).
5. **v4 split (REQ-006).** Seed 4079, own templates, class plan below. Builder refuses: any fact pattern
   used by v2/v3 splits; any 8-word window shared with v2, v3, SPEC-069 prompts, the analyze skill or the
   new tool descriptions; normalized-text or fingerprint collisions. Author does not open v2-test or
   v3-test prompt texts while writing templates (recorded in research.md). Class plan (100):
   disjoint-parallel 20, overlap-write 15, dependency-order 15, read-only shared 10, kind-choice probes
   ("can these run at the same time?" over disjoint files) 20, analyze-tempting phrasings ("analyze this
   plan") 10, git-branch 10.
6. **Pinned build (OD-D).** The run installs the plugin from a pinned commit recorded in the freeze.

## Validation strategy

| REQ | SC | Test | Planned evidence |
|---|---|---|---|
| REQ-001 | SC-001..003 | `tests/test_tooling_mcp_units_redirect.py` | unit test output |
| REQ-002 | SC-004, SC-005 | same file | unit test output |
| REQ-003 | SC-006 | `tests/test_tooling_mcp_descriptions.py` | frozen-text test |
| REQ-004 | SC-007 | same file | frozen-text test |
| REQ-005 | SC-008 | `tests/test_release_records.py` (existing) | release record + `docs/tooling/NATIVE_PLUGINS.md` diff |
| REQ-006 | SC-009 | `scripts/spec079_build_v4.py --check` | build report |
| REQ-007 | SC-010 | `scripts/spec079_build_v4.py --gate0` | `evidence/gate0-v4-report.json` |
| REQ-008 | SC-011 | `scripts/spec079_freeze.py --check` | `prompts/FREEZE-v4.json` |
| REQ-009 | SC-012 | `agent_braid/lightning_heldout_v2.analyse` | `evidence/gate-v4-report.json` |
| REQ-010 | SC-013 | converge review | spec.md result section |
| REQ-011 | SC-014 | `tests/test_spec079_boundaries.py` | frozen-path diff check |

Negative controls: SC-002, SC-003, SC-005, Gate 0 nulls. Labels are scorer outcomes (no human proxy
labels); the only human judgment is the SPEC-078 zero-prompt review (`model` vs `instrument`), done by the
owner on redacted transcripts, with any disagreement recorded verbatim. Missing results (rollout error,
quota stop) are reported and count as misses. Abstention: not applicable. Calibration: not claimed. Cost:
300 rollouts, EUR 0; Gate 0 and all build checks spend no quota.

## Constitution check after design

Unchanged: no execution authority added, no new dependency, no paid route, frozen paths untouched,
preregistration precedes observation. No blocker.

## Human review and unresolved decisions

OD-A to OD-D decided 2026-11-22. Owner yes still required for: the v4 freeze review, the rollout run,
the zero-prompt classification and the release. No open scientific question beyond H1-H4. H4 reports `validWithinRetry` because a refused first attempt cannot pass the first-attempt gate.
