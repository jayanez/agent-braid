# Implementation plan — SPEC-053

Status: draft plan. Planning is not permission to implement or deliver. REQ-001 and
REQ-002 are actionable now (structural checks and a founder signature). REQ-003 to
REQ-010 are **BLOCKED by G0**: this plan and the contracts are draft design only, and no
implementation, schema adoption or release for them starts until the founder freezes the
preregistration, runs it and records a pass (through criterion C1b; C1a informs release R1 only). A `g0-fail` or
`g0-inconclusive` outcome closes or leaves them blocked, and that is a valid
completion of the protocol. Nothing in this plan freezes, signs, approves, runs a
workflow, spends money, publishes or creates a remote issue. `obtained_evidence` is
empty and human review is pending.

## Technical context and scope

- Milestone: M4.6 — Claude Code dynamic workflows. Program:
  [SPEC-052 program](../052-claude-workflow-gate/program.md). This spec owns gate G0
  and, behind it, the transcript adapter (PR5) and gate v2 (PR6).
- Language and stack: Python 3.12+ standard library plus the pinned
  `requirements-speckit.txt`/`requirements-dev.txt` tooling (`jsonschema` is already
  used by the SPEC-023 tests). Unit tests use `unittest` (no new test stack).
- Existing code relied on (read, not changed by this plan): `agent_braid/analysis.py`
  (unchanged), `agent_braid/trace_adapter.py` (unchanged, SPEC-023 owned),
  `agent_braid/git_process.py` (bounded read-only Git calls), `agent_braid/git_adapter.py`
  (resource naming), `agent_braid/cli.py` (one additive subcommand).
- Inputs that exist now: the G0 proposal and inputs record, the pinned structural
  checker `scripts/validate_claude_workflow_g0_proposal.py` with
  `tests/test_claude_workflow_g0_proposal.py`, the draft
  [budget and source decision](budget-and-source-decision.md) (unsigned; the 2026-10-24 chat declaration applied to revision 1 bytes and is superseded by revisions 2 and 3), and
  hypothesis H-CW1 (untested).
- Out of scope, unchanged from the spec: any execution, grant, merge or promotion;
  live capture or hooks; edits to `analysis.py`; changes to SPEC-023 acceptance;
  other hosts; speed claims; any claim that transcript evidence proves commutation.
- Spend: EUR 0 additional, existing subscription, included quota only
  ([budget](../../docs/tooling/BUDGET.md)); stop on quota exhaustion.

## Constitution check before research

Applicable: clause zero and Articles 1, 5, 7, 12, 13, 15, 19, 20, 21, 23 and 25,
as listed in `assurance.json`. Also GOVERNANCE.md, the operational semantics, claim
discipline, ADR 0014, 0021 and 0024, `docs/architecture/AGENT_INTERACTION_METADATA.md`
and SPEC-023/SPEC-052.

| Authority | Obligation | How the plan honors it | Verdict |
|---|---|---|---|
| Clause zero | No assumption that Yang–Baxter or commutation applies; no claim from analogy | The mapper is an engineering definition; no braid or commutation claim; independence is never concluded from transcripts | No conflict |
| Art. 1 | Interactions over prompts | Gating and conversion are scripted/computed, not prompted | No conflict |
| Art. 5 | Effects first-class; hidden effects surfaced as uncertainty | Reads and writes are effects; `Bash`, search, MCP and unlisted tools become `unknown`; coverage is always `partial` | No conflict |
| Art. 7 | Distinguishable decision stages, provenance | Effect acquisition (mapper) is separate from analysis (`analyze`) and from the gate; provenance file binds source, projection, report | No conflict |
| Art. 12 | Prompts never replace concurrency control | No hazard decision is delegated to a model; the converter and the merge into v2 are deterministic code | No conflict |
| Art. 13 | Properties and evidence explicit; no conflation | Transcript effects are `inferred`, assurance class 0, `independence` by `declared` method; heuristic vs empirical vs formal kept apart | No conflict |
| Art. 15 | Effect semantics without coupling the core to a vendor | Mapper in its own module; `analysis.py` and the AIM schema gain no vendor field | No conflict |
| Art. 19 | Real, measurable problem; success is conflicts prevented, not agent count | G0 measures against a serial-merge-plus-tests reference on designed multi-worktree runs; no agent-count success | No conflict |
| Art. 20 | Analysis separate from execution | Read-only conversion; `executionAuthorization: false` everywhere; no grant, merge or promotion | No conflict |
| Art. 21 | Engineering and research value together | Engineering is gated behind a falsifiable experiment whose failure is acceptable | No conflict |
| Art. 23 | Evidence-building phases, no back-projection | Operational-foundation phase only; no later vocabulary used as proof | No conflict |
| Art. 25 | Objective stays an algebra of interaction, not a product claim | No algebraic claim is made | No conflict |
| ADR 0021 | Grant issuance is never model-callable; host approval is not authority | Gate v2 carries no authority; host per-run approval is a convenience only | No conflict |
| ADR 0024 | Native plugin component set | This spec adds no plugin component; the workflow component is SPEC-052's feature-local ADR proposal (not adopted) | Dependent on SPEC-052 ADR outcome for PR6 |

No MUST contradiction is found. SHOULD deviations: none identified. Items that need
reviewer attention are listed under "Human review and unresolved decisions".

## Research, assumptions and alternatives

Decisions, alternatives and primary sources are in [research.md](research.md). Research
decision ids are `RS-n`, so that they cannot be confused with the release names R1
(commit-level gate) and R2 (release with transcripts). Summary of the load-bearing ones:

1. The mapper is a **separate module** (`agent_braid/claude_transcript_trace.py`);
   `trace_adapter.py` stays byte-identical (RS-1).
2. `readVersions` for a base read is `0`, with the Git object id carried in a
   provenance table (RS-2).
3. Coverage is always `partial`; losses are counted, not escalated to `unknown` (RS-3).
4. The subagent transcript line schema is **unconfirmed** and is pinned only after
   the pre-freeze layout and tool-name census (T002) that precedes the probe, its hash and the G0 freeze (RS-4).
5. Gate v2 reaches the converter through the bundled CLI (a new additive subcommand
   `analyze-claude-transcripts`) under the constrained Bash that SPEC-052 defines (REQ-016(d)) plus that one subcommand as a planning amendment approved by the founder on 2026-10-24, used alongside the MCP tools; no new MCP
   tool (RS-9). The conversion is folded into the existing analyze-phase agent, so
   SPEC-052's four-agent bound is unchanged. This is the main feasibility dependency of
   REQ-009; if it fails the transcript part of the gate is no-go.
6. The v2 result is a new `schemaVersion` overlaid on the committed SPEC-052 v1 schema,
   with an arguments overlay for transcript inputs and opt-in path republication
   (RS-10). The product retention label is `allowlisted-metadata-and-counts`; the label
   `aggregate-only` is kept for the G0 probe (RS-7).

Assumptions, each unverified until stated otherwise: the founder's own sessions on
an owner-controlled repository are the only source; provider-terms confirmation is
pending; transcripts are available for the probe (otherwise Git arms only);
SPEC-052's v1 gate exists before PR6.

Empirical-protocol planning (gate G0) follows the preregistration as drafted, including
its review amendments (C1 split into C1a and C1b, C2 compared with the prevalence and the
naive path-overlap precision, a fixed order of evaluation):
source permission and yield come first (signature renewal against the final revision 3 bytes, layout and tool-name census whose aggregate result is recorded in revision 3, probe including the attribution-coverage comparison written and tested on a de-identified real fixture, yield estimate and `plannedRunCount`, probe and runner hashes, power operating point accepted, then freeze), designed overlap
limits generalization, the reference outcome is observed (serial merge plus tests
twice), predictions are hashed before it exists, no human label is used, the run is
the held-out unit, and missing probe data is reported per run. There is no model
fitting; the "frozen rubric" is the mechanical eligibility and exclusion list.
Absent eligible data is a feasibility result (`g0-inconclusive`), not a reason to
change the population after labels are seen. Cost components are recorded when the
host exposes them and reported as unavailable otherwise.

## Design and compatibility

### File-level design (PR5, blocked by G0)

| Path | Change | Purpose | Requirements |
|---|---|---|---|
| `agent_braid/claude_transcript_trace.py` | New | Streaming reader, closed tool table, read binding, projection builder, admission check, provenance; fixed diagnostic codes | REQ-003 to REQ-007 |
| `agent_braid/cli.py` | Additive | New subcommand `analyze-claude-transcripts`; the `analyze-trace` parser and branch are not edited | REQ-003, REQ-008 |
| `tests/test_claude_transcript_trace.py` | New | Mapping table, read binding, coverage, admission, bounds, privacy sentinels, no-network, SPEC-023 preservation | REQ-003 to REQ-008 |
| `tests/fixtures/claude_transcript/` | New | Synthetic transcript lines and a fixture Git repository builder; no real transcript | REQ-003 to REQ-007 |
| `scripts/validate_change.py` | Additive rule | Explicit sensitive rule for the new module and tests so they are not an unowned-path fallback | REQ-008 |
| `agent_braid/trace_adapter.py`, `agent_braid/analysis.py` | **Unchanged** | Proven unchanged by a diff check and by the unmodified SPEC-023 suites | REQ-003, REQ-008 |

Contracts: [contracts/transcript-mapping.md](contracts/transcript-mapping.md) (tool
table, coverage rule, allowlist, bounds, admission, provenance),
[contracts/aim-trace-record.example.json](contracts/aim-trace-record.example.json),
[contracts/gate-result-v2.md](contracts/gate-result-v2.md) and
[the schema fragment](contracts/gate-result-v2.delta.schema.json).

### File-level design (PR6, blocked by G0, PR5 and SPEC-052 v1)

| Path | Change | Purpose | Requirements |
|---|---|---|---|
| `integrations/agent-braid/plugin/workflows/braid-gate.js` | Modified (file created by SPEC-052 PR2) | Optional transcript inputs; one agent runs the CLI conversion; degrade-only handling; v2 assembly by script | REQ-009, REQ-010 |
| `scripts/build_native_plugin.py` | Modified if the inventory changes | Byte-stable inventory entry for the changed workflow | REQ-009, REQ-010 |
| `tests/test_plugin_package.py` and a new static test for the workflow | Modified/new | Static inspection (no fan-out, no edits), package verification, v1 unchanged without transcripts, v2 schema | REQ-009, REQ-010 |
| `docs/tooling/CLAUDE_WORKFLOWS.md` | Modified (created by SPEC-052) | Recipe update: transcript inputs, what v2 returns and does not, host-verification status | REQ-009, REQ-010 |
| `specs/052-claude-workflow-gate/` result and arguments schemas | Referenced, not edited from here | The v1 field names are known and the contracts here are written against them; re-check at PR6 for later SPEC-052 changes. SPEC-052 needs a reviewed amendment for validated path tokens in prompts | REQ-009, REQ-010 |

Compatibility: additive to AIM `0.2.0-draft`, the analysis report and the SPEC-052
gate. No change to `analysis.py`, SPEC-023 acceptance, the AIM schema, the plugin
MCP tool set or its limits (4 active calls, 32 operations, 1 MiB, 360 s). Replay and
the owned runtime stay at 4 operations. The commit-level gate evidence stays correct
and useful if G0 fails. Rollback of PR5/PR6 is deletion of the new module,
subcommand and workflow branch; no stored state is migrated.

Interfaces and data models are specified only in `contracts/` and are drafts.

## Validation strategy

### Validation profile

Per `docs/development/VALIDATION_PROFILES.md`: run
`python3 scripts/validate_change.py --base develop --profile quick` after each
coherent increment and `--profile pr` once on a stable candidate. This feature
touches sensitive paths, so the planner escalates: `specs/**` (feature assurance),
`integrations/**` (PR6), `scripts/build_native_plugin.py` (PR6),
`agent_braid/trace_adapter.py` (not edited; if review forces the fallback in
research RS-1 it becomes edited and the SPEC-023 owner's review is mandatory) and
`docs/adr/**` (not edited by this feature; any ADR for the mapper is a separate
change). The new module and tests need the explicit rule listed above. Neither
profile implies clean-room reproduction, evidence capture, human review or founder
approval; those remain separate gates.

For this delivery (PR1, documents only) the checks are the Spec Kit structural gates
and the tracking source inventory; no code exists.

### Requirement to scenario to test to evidence

| REQ / SC | Test or procedure | Planned evidence | Now |
|---|---|---|---|
| REQ-001 / SC-001 | `tests/test_claude_workflow_g0_proposal.py`, `scripts.validate_claude_workflow_g0_proposal` | Command, hashes, outcome | Actionable; structural only |
| REQ-002 / SC-002 | Same test file (decision record test) | Command, hashes, outcome | Actionable; signature pending |
| REQ-003 / SC-003 | procedure_req_003 → `tests/test_claude_transcript_trace.py` | Mapping-table cases, byte-identical analysis of non-Claude inputs | Blocked by G0 |
| REQ-004 / SC-004 | procedure_req_004 → same file, fixture Git repository | Base-blob binding, exclusions, loss counts | Blocked by G0 |
| REQ-005 / SC-005 | procedure_req_005 → same file | Coverage never complete, failed calls, inferred channel | Blocked by G0 |
| REQ-006 / SC-006 | procedure_req_006 → same file | Admission matrix; synthetic path byte-for-byte unchanged | Blocked by G0 |
| REQ-007 / SC-007 | procedure_req_007 → same file | Bounds, sentinels, no network, retention label and named non-aggregate items | Blocked by G0 |
| REQ-008 / SC-008 | procedure_req_008 → unmodified `tests/test_trace_adapter.py`, `tests/test_trace_lifecycle_spikes.py`, `analyze-trace` checks, diff of `trace_adapter.py` | Pass without edits; SPEC-023 owner review record | Blocked by G0 |
| REQ-009 / SC-009 | procedure_req_009 → workflow static test and package tests | Transcript inputs, single-agent conversion, degrade-only | Blocked by G0 and SPEC-052 v1 |
| REQ-010 / SC-010 | procedure_req_010 → v2 schema tests, v1 consumer tests, overlay composition check | Label preservation, baseline unchanged, `schemaVersion` dispatch, migration note | Blocked by G0 and SPEC-052 v1 |

Negative controls and boundaries (each paired with its positive case): removed or
relaxed G0 threshold, false freeze and path-retaining probe are rejected (existing);
for PR5: oversized file/line, too many transcripts or paths, duplicate JSON member,
non-finite number, symlink and special file, secret-like sentinel strings in prompts
and tool output that must never appear in any output or diagnostic, unlisted tool
names, MCP names, failed and unpaired calls, own-write read, absent-at-base read,
outside-worktree read, symlink base entry, missing/mismatched/expired admission,
unchanged synthetic input, socket creation forbidden, and a transcript with no
recognized record. For PR6: missing, unreadable, oversized, unrecognized transcript
degrades only transcript evidence; no transcripts yields the unchanged v1 result;
`executionAuthorization` other than false fails.

Conformance check: the mapper and the pinned G0 probe run on the same synthetic
fixture and every counted difference is reported, not suppressed.

Native or interactive acceptance (transcript layout census before the freeze; plugin MCP
tools, Bash constraint and nested calls inside workflow agents) needs its own
founder observations and is never implied by a passing test run.

### Evidence handling

`assurance.json` stays `draft` with `obtained_evidence: []`. Obtained evidence is
added only from commands that actually ran, with raw results, environment and
provenance, and negative or inconclusive outcomes are recorded as such. The
current authority snapshot is refreshed with
`python3 -m scripts.validate_spec_kit snapshot specs/053-claude-transcript-trace-adapter`
(which also resets human review to pending). Freezing a clean candidate commit with
`freeze` is a later, explicit step.

## PR and gate sequence for this spec

Each item is a separate reviewed change. No date or effort estimate is stated.

1. **PR1 — specs.** SPEC-053 spec, this plan, research, contracts, quickstart,
   validation plan, tasks, assurance record and draft tracking. Documents only.
2. **Founder pre-freeze steps (not a PR).** Renew or amend the signature of the budget and source
   decision (REQ-002); run the transcript layout and tool-name census, write the probe against the
   observed layout and hash the probe and runner (T002); fill the pre-freeze bindings and freeze the
   preregistration explicitly (REQ-001, T003). The workflow script, run manifest and probe script stay
   outside the repository; their hashes are pinned before the freeze.
3. **G0 run (founder).** At least 10 and at most 14 started runs of 3 or 4 worktree
   agents on the existing subscription; predictions hashed before the reference
   outcome; host per-run approval for each workflow.
4. **PR4 — G0 evidence and decision record.** Aggregate report with exclusions,
   counts, costs and protocol adherence assessed separately from the result;
   founder decision `g0-pass`, `g0-fail` or `g0-inconclusive`; independent review.
   *Kill path:* on `g0-fail`, adoption track AT-2026-006 moves to watch or rejected,
   SPEC-053 closes as not adopted and M4.6 closes with R1 only. On
   `g0-inconclusive`, REQ-003 to REQ-010 stay blocked and a new preregistration is a
   new proposal, never an amendment of the frozen one.
5. **PR5 — adapter** (only after `g0-pass`; re-plan first, pin the transcript
   schema, decide the ADR question). Test-first.
6. **PR6 — gate v2** (only after `g0-pass`, PR5 and SPEC-052 v1; re-check the contracts
   against the then-current SPEC-052 v1 schemas and the host-verification outcomes).
7. **R2 — release with transcripts** (founder decision; plugin-dist publication is
   the founder's, never this feature's).
8. **Closure** (radar milestone review, technical review, founder closure).

Gate G0 blocks PR5, PR6 and R2, and only criterion C1b (with C2 and C3) can unblock them. R1
(commit-level SPEC-052 gate) is independent of G0; C1a informs R1 and unlocks nothing.

## Risks

| Risk | Effect | Handling |
|---|---|---|
| The transcript line schema differs from the expectation or changes between host versions | Mapper rejects or mis-maps | Pin from the pre-freeze census; a later difference is `probe-unavailable` and unrecognized shapes are refused; record host versions; a fixture-only mapper is not evidence of real behavior |
| Most file changes come through `Bash` (the census shows `Bash` at 80.2% of calls) | Low attribution coverage; transcripts cannot explain the writes | This is exactly C3; coverage below 0.60 is a valid `g0-fail`; the call-share unknown rate is descriptive only |
| Gate v2 has no safe interface to the converter (Bash cannot be constrained, no MCP tool, or the SPEC-052 amendment for validated path tokens is refused) | REQ-009 infeasible | Transcript part of the gate is no-go; commit-level gate unaffected; recorded as a negative result |
| Private content reaches an output or diagnostic | Privacy breach | Allowlist, aggregate counts, fixed codes, sentinel tests, independent privacy/security review record |
| Paths are sensitive metadata | Disclosure when republished | Honest retention label and named non-aggregate items; the admission record names path disclosure; the gate republishes transcript paths only on operator opt-in; keep artifacts local |
| Sibling module breaks if SPEC-023 public names change | Mapper stops working | Test pins imported names; SPEC-023 owner review |
| The mapper and the G0 probe disagree | Misleading reading of G0 | Conformance check reports differences; the preregistered C3 (attribution coverage) stays the probe's |
| Designed overlap on one repository is read as general | Overclaim | Limits restated in every report; no prevalence, effectiveness or speed claim |
| Quota exhaustion or host change mid-G0 | Fewer eligible runs | `quota-exhausted` exclusion; `g0-inconclusive` is a valid outcome; no paid capacity |

## Constitution check after design

Re-checked against the design above: effects remain first-class and hidden effects
are surfaced as `unknown`; the core (`analysis.py`, the AIM schema) gains no vendor
coupling; analysis and execution stay separate with `executionAuthorization: false`;
no hypothesis is assumed true; coverage can never reach `complete` from transcripts;
and no authority file is edited by this feature. No MUST conflict was introduced by
the design. The open items below are reported rather than resolved.

## Human review and unresolved decisions

- Founder: sign, amend or reject the budget and source decision; confirm the
  provider-terms position for local analysis of one's own session files; freeze or
  not freeze the preregistration; the G0 disposition; R2 and closure.
- SPEC-023 owner: review the additive dependency and the unchanged-importer proof;
  decide whether a canonical ADR is required for a new mapper and admission kind
  (research RS-12).
- Founder: confirm or amend the review amendments to the G0 parameters (C1a/C1b, the C2
  comparisons, the order of evaluation) when freezing; they are recorded in the spec
  Clarifications as draft, not yet founder-confirmed.
- Spec owner and founder: the restated SC-010 (bounded sense of "v1 consumers keep
  working") and the REQ-009 interface now written in the spec are drafts for their
  confirmation.
- SPEC-052 owner: a reviewed amendment that admits validated path tokens (and the
  transcript argument members) beside validated identifiers in agent prompts; the
  conversion folded into the analyze-phase agent keeps the four-agent bound.
- Pending, not decided here: the transcript schema pin, the exact `readVersions`
  provenance field names beyond the draft, and host verification of the converter path.
  Settled and no longer pending: the bound values (confirmed 2026-10-23), the SPEC-052 v1
  field names (committed contracts, used by gate-result-v2.md), and that an inconclusive
  G0 is never amended (any new preregistration is a separate founder decision).
- Technical review, independent review and radar milestone review: pending.
