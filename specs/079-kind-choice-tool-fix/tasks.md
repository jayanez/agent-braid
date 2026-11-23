# SPEC-079: Tasks

**Milestone:** BL.2c — Tool-level kind-choice fix.

Stable task IDs. Completion requires obtained evidence; task completion does not
imply owner acceptance or support for H1-H4. Parallelizable is a dependency
property and does not authorize concurrent agents. One pull request per task; the
owner approves each merge. No task spends quota before T007's freeze and the
owner's yes.

`quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P0 — tool change (no quota)

- [ ] T001 (REQ-001, REQ-002 / SC-001..SC-005): Disjoint `units` refusal with code `units-cannot-answer-independence`, redirect message (<= 400 chars) and the constructed AIM envelope (coverage partial); non-disjoint, mixed and malformed declarations unchanged (negative controls SC-002, SC-003, SC-005). Files: `agent_braid/tooling_mcp.py`, `tests/test_tooling_mcp_units_redirect.py`. Dependencies: none. Verification: `python -m unittest tests.test_tooling_mcp_units_redirect tests.test_tooling_mcp` and `quick`.
- [x] T002 (REQ-003, REQ-004 / SC-006, SC-007): Rewrite the `analyze-work` per-kind and description-only help (drop the bare digest precondition) and add the `analyze` description pointing to `analyze-work`; frozen-text and D12 size-cap tests. Files: `agent_braid/tooling_mcp.py`, `tests/test_tooling_mcp_descriptions.py`. Dependencies: none (parallelizable with T001 by dependency only). Verification: `python -m unittest tests.test_tooling_mcp_descriptions` and `quick`.
- [x] T003 (REQ-005 / SC-008): Record the behaviour change in `docs/tooling/NATIVE_PLUGINS.md` as pending release; the release record entry is added in T010. Dependencies: T001, T002. Verification: `python -m unittest tests.test_release_records`.

## Phase P1 — held-out v4 (no quota)

- [ ] T004 (REQ-006 / SC-009): Class plan (100 prompts: disjoint-parallel 20, overlap-write 15, dependency-order 15, read-only shared 10, kind-choice probes 20, analyze-tempting 10, git-branch 10), new templates, `scripts/spec079_build_v4.py` (seed 4079) with leakage checks against SPEC-069, v2 and v3 sets, the analyze skill and the new descriptions; the author does not open v2-test or v3-test prompt texts. Files: `scripts/spec079_build_v4.py`, `specs/079-kind-choice-tool-fix/prompts/v4-test.json`, `tests/test_spec079_set.py`. Dependencies: T002. Verification: `python -m scripts.spec079_build_v4 --check`; a build that cannot reach 100 valid cases is reported as a feasibility failure.
- [ ] T005 (REQ-007 / SC-010): Gate 0 on v4: references valid, literal follower, null baselines below OD-1. Files: `specs/079-kind-choice-tool-fix/evidence/gate0-v4-report.json`. Dependencies: T001, T004. Verification: `python -m scripts.spec079_build_v4 --gate0 specs/079-kind-choice-tool-fix/evidence/gate0-v4-report.json`.
- [ ] T006 (REQ-008 / SC-011): Write `evaluation-protocol.md` preregistering H1-H4, OD-1 gate, the REQ-012 shadow-check thresholds, 100x3, `claude-code` + `claude-sonnet-5-5`, pinned plugin commit, analysis, zero-prompt review and stopping rules (quota stop, canary hit). Dependencies: T005. Verification: owner review of the protocol text.
- [ ] T007 (REQ-008, REQ-011 / SC-011, SC-014): Freeze protocol, split, builder, Gate 0 report and pinned plugin commit by sha256 on a develop commit (`scripts/spec079_freeze.py`, `prompts/FREEZE-v4.json`); boundary test that no frozen SPEC-078/069 path changed. Files: `scripts/spec079_freeze.py`, `tests/test_spec079_boundaries.py`. Dependencies: T006 merged. Verification: `python -m scripts.spec079_freeze --check`.

## Phase P2 — gate run (300 rollouts, owner yes required)

- [ ] T008 (REQ-009 / SC-012): One run of the fixed tool + current skill on v4 (300 rollouts, EUR 0); report passing share with Wilson bounds, per-class pass rates, `validWithinRetry` share (H4), `units` usage, `analyze`-only failures, missing results as misses. Files: `specs/079-kind-choice-tool-fix/evidence/gate-v4-report.json`. Dependencies: T007, owner yes. Verification: `agent_braid.lightning_heldout_v2.analyse` on the run directory.
- [ ] T009 (REQ-009, REQ-010 / SC-012, SC-013): Zero-prompt review: owner classifies each 0/3 prompt as `model` or `instrument` on redacted transcripts; an `instrument` finding invalidates the run and needs a new split version; disagreements recorded verbatim. Dependencies: T008. Verification: review record in `reviews/`.
- [ ] T010 (REQ-005, REQ-010, REQ-012 / SC-008, SC-013, SC-015, SC-016): Converge: record the H1-H4 outcomes (supported, not supported or inconclusive) and the gate verdict; release the tool change in the next alpha with its release record only after this result (OD-D) and a passing REQ-012 real-session shadow check (OD-E, read-only, thresholds frozen in T007; SC-015, SC-016); v4 is not reused for a second arm. Dependencies: T009. Verification: `python -m scripts.validate_spec_kit` and owner review.
