# SPEC-089: Analyze-work validity on Codex and OpenCode (skeleton)

**Milestone:** Host parity (owner decision of 2026-11-27, phase F7 of the cleanup plan).
Third specification of the umbrella. It is the measurement spec that
[issue #1700](https://github.com/jayanez/agent-braid/issues/1700) (Deferred) names as
its home, decided by the owner on 2026-11-26 (`docs/development/deferred-triage-20261126.md`,
read only).

**Status:** draft, **skeleton**. This document states the problem, the evidence, the
scope, the dependencies and the open decisions. It does **not** contain a measurement
design: no validity definition, no split, no gate, no sample size, no analysis and no
run plan. Those are open decisions of the owner (below) and are written only after
them. Nothing is implemented, run or published, and nothing here authorizes a run.

## Purpose and scope

[SPEC-079](../079-kind-choice-tool-fix/spec.md) fixes and measures `analyze-work`
first-attempt validity on `claude-code` only (its scope and OD-C). The fix lives in the
shared MCP server (`agent_braid/tooling_mcp.py`, used by `plugin_mcp.py`), which the
Codex and OpenCode plugins also load. Every host therefore receives the code, but only
Claude Code is measured. This specification is the place to decide whether and how to
measure Codex and OpenCode after the fix.

Evidence (SPEC-069 T010 held-out run, set `spec069-held-out-v1`, 10 prompts by 3
repetitions, arm `final`; the set is spent; source:
`docs/tooling/NATIVE_PLUGINS.md` section "Measured host validity",
`specs/069-aim-request-authoring/evidence/native-runs-t010-heldout-final*.json`, and
#1343):

| Host | Valid at first attempt (Wilson 95%) | Prompts valid (of 10) | Missed prompts |
|---|---|---|---|
| Claude Code | 27/30 (0.74 to 0.97) | 9 | HELD-04 |
| OpenCode | 27/30 (0.74 to 0.97) | 9 | HELD-04 |
| Codex | 24/30 (0.63 to 0.90) | 7 | HELD-02, HELD-04, HELD-05 |

The D4 target was not met on any host and the owner accepted that as a documented
deviation on 2026-11-12; it is not a pass. HELD-04 failed on every host with one
signature that SPEC-078 and SPEC-079 treat separately; the causes of HELD-02 and
HELD-05 on Codex are unexplained.

Unmeasured, from #1700:

- Codex and OpenCode validity after the SPEC-079 tool change.
- The unexplained HELD-02 and HELD-05 results on Codex.
- SPEC-069 D4 against SPEC-078 OD-1 on those hosts.

Prerequisite: the Lightning runner has no Codex host
(`agent_braid/lightning_config.py` `HOSTS`; `lightning_evaluation.py:34`
`REQUIRED_HOSTS = ("claude-code",)`). [SPEC-088](../088-lightning-codex-host/spec.md)
adds Codex as a rollout host; OpenCode is a declared limit
(`route-unverified`: no credential source reported, SPEC-071 OD-2).

This is a **research measurement specification in skeleton form**. What it will have to
decide is listed as open decisions, and the constraints that bind it are listed as
requirements.

Out of scope (each is stated as a requirement with its REQ ID below):

- Any tool, skill or scorer change (REQ-003).
- Reusing a spent held-out set, including `spec069-held-out-v1` (REQ-002).
- A claim for a host that was not measured (REQ-004).
- Running anything before the owner authorizes it (REQ-007).

## Authorities

[CONSTITUTION.md](../../CONSTITUTION.md) clause zero and Articles 0, 5, 13, 14, 19, 20;
[GOVERNANCE.md](../../GOVERNANCE.md);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md) (EUR 0
subscription route). Read, not edited: SPEC-069, SPEC-078, SPEC-079, SPEC-088. No
authority conflict found. Document hashes are kept in `assurance.json`.

## Requirements and acceptance scenarios

These requirements are the constraints of #1700 stated as requirements. They do not
define the measurement; the measurement design is added after the owner decisions.

**REQ-001 Owner decisions before design.** The validity definition, the fresh held-out
split (preregistered, frozen, with Gate 0) and the run authorization are decided by the
owner in dated records before any measurement design, preregistration or run plan is
written in this specification.

- **SC-001:** Given the specification, when its tasks are listed, then no design,
  preregistration or run task precedes the owner-decision task (T001), and no section
  states a validity definition, split, gate, sample size or analysis.

**REQ-002 No reuse of spent sets.** The measurement MUST NOT use a held-out or test set
that has been spent or opened, including `spec069-held-out-v1`, the SPEC-078 and
SPEC-079 splits and their test sets. It uses a fresh split, preregistered and frozen
before any run, with Gate 0.

- **SC-002:** Given the frozen split of a later task, when it is compared with the
  recorded hashes of every earlier held-out and test set, then it shares no prompt with
  any of them.

**REQ-003 No tool, skill or scorer change.** The measurement MUST NOT change the MCP
tool, the skills, the guidance bytes under test or the scoring rules.

- **SC-003:** Given the change set of this specification, when its paths are listed,
  then none is a tool, skill, guidance or scorer file.

**REQ-004 No claim for an unmeasured host.** The report MUST NOT
state a validity result for a cell without recorded results.

- **SC-004:** Given the final report, when each claim is traced, then it names a host,
  model, build and set that has recorded results.

**REQ-005 Unmeasurable host is `unobserved`.** A host that cannot be measured (for
example a `route-unverified` host or one without an executable) is recorded as
`unobserved` with the reason, and is neither dropped silently nor filled in.

- **SC-005:** Given a host that cannot run, when the report is produced, then the host
  appears with outcome `unobserved` and its reason.

**REQ-006 Reported outcome, including a missed gate.** The report gives the per-host
rate with Wilson bounds and the per-class rates; a missed gate is a valid outcome and is
reported as such. (The report's exact fields are decided with the design.)

- **SC-006:** Given a run whose gate is missed, when the report is produced, then the
  outcome is recorded as missed and the specification is still complete.

**REQ-007 No run without authorization.** The measurement runs once per host on the
subscription route (EUR 0, no API key) and only after the owner's explicit, dated
authorization of that run. This specification grants no execution authority.

- **SC-007:** Given any run record, when it is inspected, then it cites the owner's
  authorization and the subscription route, and `executionAuthorization` is `false` in
  every plan output before that authorization.

**REQ-008 Leaves skeleton only after its dependencies.** The skeleton is expanded into a
measurement design only after SPEC-079 T010
([#1513](https://github.com/jayanez/agent-braid/issues/1513)) has converged and the
owner records the decisions of REQ-001; the Codex host path of SPEC-088 is required
before a Codex run.

- **SC-008:** Given the dependency records, when the first design task is created, then
  SPEC-079 T010 is converged and the owner decisions are recorded.

## Non-functional requirements

- Cost: EUR 0 on the subscription route; no paid API route (REQ-007).
- Reproducibility and size limits: decided with the design; none stated here.

## Security and privacy

- No credential is read from a file, written or logged; no provider key is accepted
  (REQ-007).
- Transcripts follow the SPEC-074 consent and redaction rules; no unconsented
  content-bearing trace is written.
- A capability flag is not an authorization (SPEC-087 REQ-014; REQ-007).

## Terminology

- **Validity (first-attempt):** open; its definition is OD-A. SPEC-069 D4 and SPEC-078
  OD-1 are earlier definitions and are not adopted here.
- **Spent set:** a held-out or test set whose prompts have been run or revealed (REQ-002).
- **Gate 0:** the pre-run check of a split (references valid, literal follower, null
  baselines) as used by SPEC-078 and SPEC-079; its content for this specification is
  open (OD-B).
- **`unobserved`:** a host recorded as not measured, with a reason (REQ-005).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Scientific boundaries and compatibility

Research measurement specification in skeleton form; no hypothesis is stated yet.

- **Domain:** to be fixed with the design; the unmeasured cells are Codex and OpenCode
  on `analyze-work` after the SPEC-079 tool change.
- **Observation contract, execution contract, hypotheses, analysis:** open; written
  after the owner decisions.
- **Limits:** the SPEC-069 T010 figures are one session set per host on a spent set with
  one host default model per host (Codex on its default model, OpenCode through
  OpenRouter); they are descriptive and do not transfer to a new split or build.
- **Compatibility:** none affected; this skeleton changes no code.

## Owner decisions

No decision is recorded. Each is open and left to the owner.

- **OD-A Validity definition (open).** What counts as a valid first attempt on each host
  (for example SPEC-069 D4, SPEC-078 OD-1, or a new definition), and whether the same
  definition applies to all hosts. Owner: the founder.
- **OD-B Fresh split (open).** A fresh held-out split, preregistered and frozen, with
  Gate 0: its construction, size and class composition. Owner: the founder.
- **OD-C Run authorization (open).** Whether and when one run per host, on the
  subscription route, is authorized. Owner: the founder.
- **OD-D Out of scope instead (open).** Alternatively, the owner records Codex and
  OpenCode validity as out of scope with a reason, which closes this specification
  without a measurement (the "done when" of #1700). Owner: the founder.
- **OD-E OpenCode route (open).** Whether OpenCode is measured through its current
  route, stays a declared limit, or is excluded; it reports no credential source today.
  Owner: the founder.

## Risks and assumptions

- Risk: a fresh split is not independent of earlier ones (REQ-002; T001 onward).
- Risk: a host that cannot be measured is silently dropped (REQ-005).
- Risk: a Codex result is read as a claim about all Codex builds or models (REQ-004).
- Assumption: SPEC-088 provides the Codex rollout host (REQ-008).
- Assumption: SPEC-079 T010 converges and fixes the tool bytes under test (REQ-003,
  REQ-008).

## Exit criteria

This skeleton is complete when the owner has recorded OD-A to OD-E (T001). It is then
either expanded into a full specification with a measurement design, or closed as out of
scope with a reason (OD-D). Nothing in the skeleton is evidence.

## Open questions

OD-A to OD-E above. Owner: the founder, at T001.

## Dependencies

- SPEC-079 T010 ([#1513](https://github.com/jayanez/agent-braid/issues/1513)) converges
  before any design (REQ-008).
- SPEC-088 (Codex as a Lightning host) before a Codex run.
- Read, not edited: SPEC-069 (evidence), SPEC-078 and SPEC-079 (splits, Gate 0),
  SPEC-071 (refusal contract), SPEC-074 (consent).
- Related host-parity gaps, not owned here: #1125, #842, #843, #1126, #1129.

## References

- [CONSTITUTION.md](../../CONSTITUTION.md), [GOVERNANCE.md](../../GOVERNANCE.md).
- [Tasks](tasks.md), [validation plan](validation-plan.md).
- [Native plugins, measured host validity](../../docs/tooling/NATIVE_PLUGINS.md).
- [Issue #1700](https://github.com/jayanez/agent-braid/issues/1700).
