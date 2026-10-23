# M4.6 — Claude Code dynamic workflows: program

Status: draft planning. Planning decisions of 2026-10-23 are recorded below (they are planning decisions, not acceptance, adoption or approval); nothing here authorizes implementation, publication, remote issue creation, concurrent agents or autonomous delivery. No dates, speed estimates or acceptance results are stated.

## Scope

Make Agent Braid usable at the end of Claude Code dynamic workflows that run worktree agents. According to its documentation, Claude Code applies no automatic merge or conflict detection to such agents. End state ("integrated"): a user installs the plugin; a workflow with worktree agents ends by calling `/agent-braid:braid-gate` (directly or nested); the gate returns commit-level evidence (read and write hazards from transcripts only if G0 passes), a `git merge-tree` baseline and, for at most four operations, a replay certificate and a prepared batch; the operator grants outside the workflow (grant-policy-run) and executes through the owned runtime, or integrates manually in the advisory order. Agent Braid ships no fan-out and makes no speed claim (parallel runtime speedup is a recorded NO-GO: SPEC-021 G4 median 0.5581, SPEC-022, SPEC-038 0.6539).

Out of scope: pre-flight partitioning (possible SPEC-054, gate G2), Codex workflows, execution authority, hooks and mods.

## Specs

| Spec | Deliverable | Depends on |
|---|---|---|
| [SPEC-052](spec.md) Claude workflow integration gate | Read-only `braid-gate` workflow packaged in the native plugin, recipe doc `docs/tooling/CLAUDE_WORKFLOWS.md`, host verification, release acceptance | Plugin 0.1.0-alpha.3 on develop; feature-local [ADR proposal](adr-proposal.md) |
| [SPEC-053](../053-claude-transcript-trace-adapter/spec.md) Claude subagent transcript to AIM trace adapter | Adapter producing AIM traces from subagent transcripts | Declared additive dependency on SPEC-023 (ADP.1, owner of `agent_braid/trace_adapter.py`), without changing SPEC-023 acceptance; gate G0 |

SPEC-052 and SPEC-053 are independent engineering tracks except gate v2 (PR6), which consumes the adapter only after G0 and PR5 and requires the SPEC-052 v1 gate.

## Gates

- **G0 — transcript-signal experiment (preregistered).** Question: do Claude subagent transcripts carry read or write signals that commit-level analysis misses, at acceptable cost and fidelity? The protocol (sampling frame, data rights, eligibility, labels, thresholds, negative and inconclusive reporting) is preregistered before any data is read. Runs on the founder's existing Claude subscription with EUR 0 additional spend (docs/tooling/BUDGET.md); no paid API, credits or upgrades. Blocks the SPEC-053 adapter implementation and gate v2. A negative or inconclusive G0 is a valid result and still allows closure.
  Preregistered rule, as summarized from [the proposal](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md), which is authoritative and not yet frozen: at least 10 eligible runs with probe data are needed. C1a (commit-level evidence: a reference failure missed by both `git merge-tree` baselines and flagged by the Braid primary flag) informs R1 only, unlocks nothing and is neither a pass nor a fail input. C1b (the only C1 criterion that gates the transcript adapter and gate v2): at least 1 reference failure missed by both merge-tree baselines, by naive path overlap and by `analyze-git` under its primary and inclusive flags, and flagged by the transcript probe. C2: read/write-overlap precision of at least 0.3 and strictly above both the reference-failure prevalence and the naive path-overlap precision. C3: unknown rate of at most 40%. Order of evaluation: fewer than 10 eligible runs with probe data is `g0-inconclusive`; otherwise C1b and C3 are evaluated and either unmet is `g0-fail` even with fewer than 3 probe-flagged runs; then fewer than 3 probe-flagged runs is `g0-inconclusive`; then C2 is evaluated and unmet is `g0-fail`; `g0-pass` needs C1b, C2 and C3 together. An inconclusive G0 never passes. Obtained evidence: none; nothing frozen or run.
- **R1 — release, commit level.** Plugin package (candidate 0.1.0-alpha.4) containing SPEC-052 only. Requires ADR adoption (PR3), host-verification outcomes, release acceptance (REQ-014). Independent of G0.
- **R2 — release with transcripts.** Only if G0 passes; includes the adapter and gate v2.
- **G2 — optional pre-flight partitioning (SPEC-054).** Requires the "Coordination across tools" contract of specs/039 (identity, concurrency, idempotency, recovery) and its own ADR. Not planned unless the founder opens it.

## PR sequence

Each item is a separate reviewed change; GitHub remote artifacts remain drafts and publication is forbidden in this delivery.

1. **PR1 — specs** (052, 053, program, the G0 preregistration proposal, milestone tracking by the integrator).
2. **PR2 — SPEC-052 implementation**: workflow source, builder change, tests, result contract, recipe doc, host-verification probes. No release, no version bump, no publication.
3. **PR3 — ADR adoption**: canonical `docs/adr` file, re-snapshot of specs 047/048/051, `authority-impact-review.json`, README and `validate_change` updates.
4. **R1 release** (founder decision on number and publication to plugin-dist).
5. **G0 run and PR4**: the preregistration proposal is already part of PR1 and is frozen by the founder before data collection; PR4 is only the evidence and decision record (positive, negative or inconclusive), as in the SPEC-053 plan.
6. **PR5 — SPEC-053 adapter** (only if G0 passes).
7. **PR6 — gate v2**: transcript-derived hazards in the gate (only if G0 passes).
8. **R2 release**.
9. **Closure**.

## Decisions recorded 2026-10-23

Answered with the founder as planning decisions (`speckit-clarify`; see the [SPEC-052 clarifications](spec.md#clarifications)). They are not acceptance, adoption or approval of anything:

- A run needs at least two distinct sources.
- Branch or tag names are accepted, resolved to full commit SHAs and re-resolved at the end; a moved reference is reported as stale.
- The baseline uses a temporary `GIT_OBJECT_DIRECTORY` with the repository store as alternate; no object reaches the repository.
- `workspaceId` is explicit; the gate never defaults and refuses on a repository-root mismatch.
- If plugin MCP tools are unavailable to workflow agents, the bundled CLI is allowed only with the Bash permission constrained to the plugin launcher (defined once in the SPEC-052 Clarifications as an explicit launcher-subcommand allowlist, never the launcher binary; the read-only `plugin workspaces` registry read is part of it as a planning interpretation pending founder review); otherwise R1 is no-go and only the recipe ships.
- Gate agents inherit the session model; no model or effort is pinned.
- PR2 may merge before ADR adoption provided no version bump, plugin-dist publication or release occurs before adoption; the builder excludes `workflows/` by default until then.
- R1 is the commit-level gate alone, expected as `0.1.0-alpha.4`, independent of G0 and subject to separate founder release acceptance.

## Founder decision points still open

1. Adopt, amend or reject the ADR proposal (PR3).
2. R1 version number confirmation, release acceptance and any plugin-dist publication.
3. G0 preregistration freeze before data collection, and G0 disposition.
4. Whether G2 (SPEC-054) is opened.
5. Remote tracking publication (milestone, issues, Project) and milestone closure.
6. The planning amendments to the constrained Bash allowlist: `plugin workspaces` for the v1 fallback registry checks, `analyze-claude-transcripts` for gate v2, and validated path tokens in gate v2 prompts (SPEC-052 Clarifications; SPEC-053 REQ-009). Not approved; pending review.

## Kill criteria

Stop or narrow the milestone, recording the reason, if any of these holds:

- A required host behavior fails verification (HV-1 plugin MCP tools in workflow agents with no acceptable CLI fallback, that is, one whose explicit launcher-subcommand allowlist the host cannot express; HV-3 nested call when it is the only integration path; the REQ-016 allowlist cannot deny `execute`, `recover`, `verify` or `status`): no R1 gate; keep the documentation recipe.
- The host removes or the organization disables workflows, or the workflow API changes so that the script cannot be validated structurally.
- The gate cannot run within the plugin lock and MCP limits for realistic inputs, or an equal-to-base or other silent false negative cannot be prevented.
- A known-answer counterexample shows the gate reports independence where merge-tree conflicts on add/modify-only history and the cause cannot be bounded in the limits statement.
- G0 negative or inconclusive: SPEC-053 adapter and gate v2 are not implemented; the milestone may close with R1 and the G0 report.
- Any step would require spend beyond EUR 0, a grant or execution inside the workflow, or a fan-out shipped by Agent Braid.

## Closure checklist

- [ ] SPEC-052 requirements implemented or explicitly dispositioned; host verification outcomes recorded; release acceptance recorded for each release made.
- [ ] G0 report published with its protocol adherence assessment and result (including negative or inconclusive).
- [ ] SPEC-053 implemented only if G0 passed, otherwise disposition recorded; SPEC-023 acceptance unchanged.
- [ ] ADR proposal adopted, amended or rejected; affected records re-snapshotted if adopted.
- [ ] Radar milestone review.
- [ ] Technical review.
- [ ] Founder closure.
