> Unpublished local draft payloads derived from `tasks.md` and `assurance.json` as they stand in this working tree. No remote issue, label, milestone, description or Project change was created, audited or applied, and none is authorized by this file. Source links target the eventual integrated `develop` branch and do not claim that these local files are already there. Refresh against the final candidate before any external use.

# Unpublished issue drafts

Milestone: M4.6 — Claude Code dynamic workflows (does not exist remotely; creation is forbidden in this delivery). One spec parent issue plus one issue per task; labels `spec` and `task`. Only the spec parent is marked Project review pending (draft flag only; tasks inherit it through the parent, the convention SPEC-052's drafts use). Tasks marked `Blocked by G0:` stay blocked unless the founder records `g0-pass`; tasks marked `Founder:` are founder actions or decisions.

## SPEC-053

Proposed state: open. Parent: none. Milestone: M4.6 — Claude Code dynamic workflows. Labels: spec. Project review: pending (draft flag).

<!-- agent-braid-spec-id: SPEC-053 -->

Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)

Requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010.

Issue state is a bounded tracking record, not a scientific or founder approval.

## SPEC-053/T001

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T001 -->

## Task

Founder: review, amend or sign the draft budget and source decision as a separate record that binds the bytes of `budget-and-source-decision.md` together with the proposal and its inputs file, and record the provider-terms position for local analysis of the founder's own session files and the manual declaration that extra usage and auto-recharge are off. Dependencies: none. Target files: a founder decision record whose location the founder chooses (not created by an agent). Acceptance: EUR 0 additional spend on the existing subscription, the transcript source scope, the G0 aggregate-only retention table and a signature are all stated; no approval is inferred from the draft. Verification: `.venv-speckit/bin/python -m unittest tests.test_claude_workflow_g0_proposal -v` still passes (structure only; a text check cannot verify consent, provider terms or a signature). Planned evidence: signed record path and SHA-256. Obtained: none; the draft remains unsigned and approval is pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-002 SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T002

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T002 -->

## Task

Founder: freeze the preregistration explicitly. Fill the pre-freeze bindings listed under `requiredBeforeFreeze` in `docs/experiments/claude-workflow-g0-inputs.json` (repository, base commit, probe script hash, runner script hash, tool versions, workflow census, signed source and budget decision, founder decision binding the proposal and inputs bytes) and record a separate freeze decision. Dependencies: T001. Target files: a founder freeze record (location chosen by the founder); no agent edits the proposal or the inputs file. Acceptance: `frozen` becomes true only through that separate record; changing a threshold, order rule, eligibility rule or arm after the first run starts invalidates earlier runs for G0. Verification: the structural checker `.venv-speckit/bin/python -m scripts.validate_claude_workflow_g0_proposal` and its unit tests, with negative controls for false freeze and changed bytes. Planned evidence: freeze record hash, proposal hash `02291d0d9cbde74222652ba6b22a4cdd0293fcf7a5aa3c6adf9a119cb6cb3e8d` and inputs hash. Obtained: none; nothing is frozen.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-001 SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T003

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T003 -->

## Task

Prepare, outside the repository and never committed, the ad-hoc dynamic-workflow script, the run manifest template and the stdlib transcript probe script, and hash their bytes before the first run; the probe retains integer counts only and never a path, a path hash, a prompt, file content or tool output. Dependencies: T002. Target files: none in the repository (private working files); the hashes go into the frozen bindings. Acceptance: the manifest records run id, base commit, task list with overlap rationale, the fixed serial merge order, test command, agent count and tool versions; the workflow only creates agents and returns branches and performs no merge. Verification: probe self-check on a synthetic transcript the founder writes; hashes recorded before run 1. Planned evidence: script hashes in the manifest. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-001 SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T004

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T004 -->

## Task

Founder: run at least 10 eligible and at most 14 started ad-hoc workflows of 3 or 4 worktree agents on the existing Claude subscription, each with the host's own per-run approval; no coding agent starts them. Dependencies: T003. Target files: none in the repository (raw transcripts, prompts, diffs and merge-tree output stay local). Acceptance: manifest hashed before launch; at least 7 of the first 10 runs with a designed file or shared-symbol overlap and at least 3 with a cross-file contract dependency; predictions of every arm hashed before the reference outcome; reference outcome by serial Git merge in the preregistered order followed by the project tests run twice; exclusions decided mechanically and counted; EUR 0 additional spend and stop on quota exhaustion, never completing a run with paid capacity. Verification: per-run checklist against the frozen inputs. Planned evidence: manifest hashes, prediction-file hashes, per-arm run-level labels, probe integer counts, costs or recorded as unavailable. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-001 SC-001 REQ-002 SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T005

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T005 -->

## Task

Write the G0 evidence report (PR4): aggregate metrics, exclusion counts by reason, the primary unknown rate (probe tool-call share) and the secondary Git-level shares, read/write-overlap precision per run with the Wilson interval as description only, replay-ineligible rate, analysis wall times, costs, and a protocol-adherence assessment kept separate from the result. Dependencies: T004. Target files: a report under `docs/experiments/` and a `specs/053-claude-transcript-trace-adapter/evidence/` record, names set at PR4. Acceptance: C1a and C1b are reported separately (C1a informs R1 only), the reference-failure prevalence and the naive path-overlap precision are reported next to the read/write-overlap precision before C2 is evaluated, and the outcome follows the preregistered order of evaluation; only the preregistered retained items are committed; limits restated (designed overlap, one repository, no prevalence, no speed or safety claim); missing and probe-unavailable runs reported with denominators. Verification: `.venv-speckit/bin/python -m scripts.validate_spec_kit` and `--profile pr`; every figure reproducible from the retained integer counts. Planned evidence: report hash and commands. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-001 SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T006

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T006 -->

## Task

Founder: record the G0 disposition as `g0-pass`, `g0-fail` or `g0-inconclusive` in a separate decision record after independent review of the PR4 report; add obtained evidence to `assurance.json` only from commands that actually ran, preserving raw results and provenance. Dependencies: T005. Target files: founder decision record; `specs/053-claude-transcript-trace-adapter/assurance.json`. Acceptance: the outcome applies the frozen rule in its order of evaluation (fewer than 10 eligible runs with probe data is inconclusive; otherwise C1b and C3 unmet is fail even with fewer than 3 probe-flagged runs; then fewer than 3 probe-flagged runs is inconclusive; then C2 unmet is fail; pass needs C1b, C2 and C3 together; inconclusive never passes), and C1a unlocks nothing; a pass adopts nothing and proves no conflict prevention. Verification: independent review record; structural gates. Planned evidence: decision record hash. Obtained: none; human review pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-001 SC-001 REQ-002 SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T007

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T007 -->

## Task

Founder: kill path on `g0-fail`. Move adoption track AT-2026-006 in `research/adoption/2026-09-initial-triage.json` to watch or rejected through its own decision record, close SPEC-053 as not adopted, leave T009 to T031 unimplemented (any tracking closure of those tasks uses the owner-adopted cancellation mechanism and is never relabeled as completed), and close M4.6 with R1 only. Dependencies: T006 with outcome `g0-fail`. Target files: the adoption triage record; the tracking configuration through its own reviewed change; a closure note. Acceptance: negative result published with counts; SPEC-052's commit-level gate is unaffected. Verification: `.venv-speckit/bin/python -m scripts.validate_spec_kit`. Planned evidence: decision record hash. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-001 SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T008

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T008 -->

## Task

Founder: handle `g0-inconclusive`. Keep REQ-003 to REQ-010 blocked, publish the counts and reasons, and treat any further attempt as a new preregistration proposal rather than an amendment of the frozen one after data were seen; whether to attempt one is the founder's separate decision. Dependencies: T006 with outcome `g0-inconclusive`. Target files: founder decision record. Acceptance: an inconclusive result is never recorded as a pass. Verification: structural gates. Planned evidence: decision record hash. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-001 SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T009

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T009 -->

## Task

Blocked by G0: Re-plan after `g0-pass`: pin the confirmed subagent transcript line shape and host versions observed on the first G0 run as the `-v1` schema pin, confirm the `readVersions` provenance table field names, ask the SPEC-023 owner and the founder whether a canonical ADR is required for a new mapper and admission kind (research RS-12), and refresh plan, research and contracts. Dependencies: T006 with outcome `g0-pass`. Target files: `plan.md`, `research.md`, `contracts/transcript-mapping.md`, `assurance.json` (re-snapshot). Acceptance: no field is read that the pin does not name; unresolved questions stay listed. Verification: `.venv-speckit/bin/python -m scripts.validate_spec_kit snapshot specs/053-claude-transcript-trace-adapter` then the full gate. Planned evidence: updated documents and re-snapshot hashes. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-003 SC-003 REQ-004 SC-004 REQ-006 SC-006
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T010

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T010 -->

## Task

Blocked by G0: Write the failing tests first (TDD) and synthetic fixtures, and confirm they fail for the intended reason before any implementation. Dependencies: T009. Target files: `tests/test_claude_transcript_trace.py`; `tests/fixtures/claude_transcript/`. Acceptance: cases for each tool class, MCP names, unlisted tools, malformed and truncated lines, failed and unpaired calls, own-write, absent-at-base, outside-worktree and symlink base entries, admission matrix, bounds, secret-like sentinels in prompts and tool output, no-network guard and a transcript with no recognized record; every positive case has a paired negative; no real transcript enters the repository. Verification: `.venv-speckit/bin/python -m unittest tests.test_claude_transcript_trace -v` shows the expected failures. Planned evidence: failing-run output retained. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-003 SC-003 REQ-004 SC-004 REQ-005 SC-005 REQ-006 SC-006 REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T011

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T011 -->

## Task

Blocked by G0: Implement the mapper `claude-subagent-transcript-v1`: closed tool table (`Read` read; `Edit`, `Write`, `NotebookEdit` write; `Bash`, `Grep`, `Glob`, MCP and every other name unknown), `git://{repoId}/{path}` resources, agent-scoped unknown resources, versioned identifier, effects only in the `inferred` channel. Dependencies: T010. Target files: `agent_braid/claude_transcript_trace.py` (new); `agent_braid/analysis.py` and `agent_braid/trace_adapter.py` are not edited. Acceptance: output validates against the unchanged AIM `0.2.0-draft` schema and adds no vendor field to it; analysis of existing non-Claude inputs is byte-identical before and after. Verification: the T010 tests for REQ-003 pass; AIM example in `contracts/` reproduced from a fixture. Planned evidence: test output and byte comparison. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-003 SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T012

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T012 -->

## Task

Blocked by G0: Implement base-blob binding and self-read exclusion using one bounded read-only Git lookup per agent through the existing bounded Git process wrapper. Dependencies: T011. Target files: `agent_braid/claude_transcript_trace.py`. Acceptance: a read of a base path emits a read effect with `readVersions` 0 and a provenance `baseBlobs` entry; reads of an own-written path, a path absent at base, a path outside the worktree or a non-regular base entry emit no read effect or version and increase the named loss counts; no filesystem access to the agent worktree and no symlink following. Verification: REQ-004 tests against a fixture Git repository. Planned evidence: test output with loss counts. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-004 SC-004
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T013

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T013 -->

## Task

Blocked by G0: Implement the coverage rule: coverage always `partial`, never `complete` and never lowered by a loss, failed or unpaired tool calls produce no effect and are counted, and no pair containing an unknown effect can be reported as an independent candidate with complete coverage. Dependencies: T011. Target files: `agent_braid/claude_transcript_trace.py`; `tests/test_claude_transcript_trace.py`. Acceptance: for Bash-only, failed-call and mixed transcripts the analyzer returns only `conflicting`, `ordered` or `unknown`; the generic importer's loss-to-unknown rule is not edited. Verification: REQ-005 tests. Planned evidence: test output. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-005 SC-005
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T014

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T014 -->

## Task

Blocked by G0: Implement the streaming converter with fail-closed bounds (at most 32 transcripts, 32 MiB per transcript, 1 MiB per line, 512 distinct paths per agent, 256-character metadata strings, depth 16), allowlisted retention under the label `allowlisted-metadata-and-counts`, provenance that names the retained non-aggregate items, fixed diagnostic codes, duplicate-member and non-finite-number rejection, and no network. Dependencies: T011. Target files: `agent_braid/claude_transcript_trace.py`. Acceptance: breaches are rejected before analysis; no prompt, file content, command text, tool output or rejected value appears in any result, provenance or diagnostic; resource paths are documented as sensitive metadata. Verification: REQ-007 tests including sentinel and socket guards. Planned evidence: test output. Obtained: none; no arbitrary-secret detection is claimed.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T015

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T015 -->

## Task

Blocked by G0: Implement the real-source admission path: new admission kind `reviewed-real-source` bound by digest to a separate admission record naming rights, allowed fields, transformations, retention (`allowlisted-metadata-and-counts`) with its retained non-aggregate items, path disclosure, privacy boundaries, mapper, schema pin and expiry. Dependencies: T011; T019 for the real record. Target files: `agent_braid/claude_transcript_trace.py`. Acceptance: missing, mismatched or expired records are rejected with fixed codes; the synthetic admission is not accepted by this converter and the existing importer does not accept the new kind; the synthetic path is byte-for-byte unchanged. Verification: REQ-006 admission matrix tests and a byte comparison of the existing synthetic fixture run. Planned evidence: test output and hashes. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-006 SC-006
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T016

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T016 -->

## Task

Blocked by G0: Add the CLI subcommand `analyze-claude-transcripts` taking a conversion request and explicit new output paths, creating outputs exclusively with owner-only permissions and refusing symlinks and collisions; do not edit the `analyze-trace` parser or branch. Dependencies: T012 T013 T014 T015. Target files: `agent_braid/cli.py` (additive); `tests/test_claude_transcript_trace.py`. Acceptance: no execution switch, no network, no grant; `executionAuthorization` false in every artifact. Verification: CLI tests plus the unmodified `analyze-trace` tests. Planned evidence: test output. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-003 SC-003 REQ-007 SC-007 REQ-008 SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T017

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T017 -->

## Task

Blocked by G0: Add the explicit `validate_change` rule for the new module and tests and implement the SPEC-023 preservation checks: the unmodified suites `tests.test_trace_adapter` and `tests.test_trace_lifecycle_spikes`, the `analyze-trace` behavior, a diff check proving `agent_braid/trace_adapter.py` and `agent_braid/analysis.py` are unchanged, and a test pinning the public names imported from `trace_adapter`. Dependencies: T016. Target files: `scripts/validate_change.py`; `tests/test_claude_transcript_trace.py`. Acceptance: SPEC-023 suites pass without modification and no SPEC-023 limit, mapper, schema or acceptance statement changes. Verification: `.venv-speckit/bin/python -m unittest tests.test_trace_adapter tests.test_trace_lifecycle_spikes -v` and `git diff --exit-code develop -- agent_braid/trace_adapter.py agent_braid/analysis.py`. Planned evidence: outputs and exit codes. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-008 SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T018

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T018 -->

## Task

Blocked by G0: Implement and report the conformance check between the pinned G0 probe and the mapper on the same synthetic fixture, listing every difference (failed-call handling, absent-at-base rule) without suppressing any. Dependencies: T011 T013. Target files: `tests/test_claude_transcript_trace.py`; a retained conformance note. Acceptance: the preregistered C3 definition is not redefined; differences are reported as counts. Verification: the conformance test. Planned evidence: report with counts. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-003 SC-003 REQ-005 SC-005
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T019

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T019 -->

## Task

Blocked by G0: Founder: author, review and sign the real-source admission record for the founder's own G0 session transcripts, stating rights, the provider-terms confirmation status, allowed fields, transformations, retention and privacy boundaries, schema pin and expiry. Dependencies: T001 T009. Target files: an admission record and its separate review record (locations chosen at PR5). Acceptance: the record's bytes match what the converter checks; it grants no approval beyond that source and scope, and its digest check proves nothing about reviewer identity. Verification: REQ-006 matrix with the valid record. Planned evidence: record hash. Obtained: none; approval pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-006 SC-006
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T020

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T020 -->

## Task

Blocked by G0: Record an independent privacy and security review of the converter: allowlist completeness, sentinel and no-network tests, path and symlink handling, output permissions, failure modes and residual risks (paths as sensitive metadata, secrets in file names undetected). Dependencies: T014 T015 T016. Target files: a review record under `specs/053-claude-transcript-trace-adapter/` named at PR5. Acceptance: negative and inconclusive findings are retained; the review is not an approval of any real transcript. Verification: review checklist executed against the candidate commit. Planned evidence: review record hash. Obtained: none; human review pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-006 SC-006 REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T021

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T021 -->

## Task

Blocked by G0: Record the SPEC-023 owner's review of the additive dependency and the unchanged-importer proof before merge. Dependencies: T017. Target files: a review record named at PR5. Acceptance: the owner confirms no SPEC-023 requirement, scenario, test, limit or synthetic-only default changed, and answers the ADR question of T009. Verification: the T017 outputs attached. Planned evidence: review record hash. Obtained: none; approval pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-008 SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T022

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T022 -->

## Task

Blocked by G0: Validate PR5 as a candidate: run `scripts/validate_change.py --base develop --profile quick` after each increment and `--profile pr` once, re-snapshot the assurance record, and add obtained evidence only from commands that ran. Dependencies: T018 T020 T021. Target files: `specs/053-claude-transcript-trace-adapter/assurance.json`. Acceptance: executed checks are separated from pending human, interactive and externally blocked checks; no clean-room, evidence capture, review or approval is implied by a profile. Verification: `.venv-speckit/bin/python -m scripts.validate_spec_kit` and the profiles. Planned evidence: command outputs and hashes. Obtained: none; human review pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-003 SC-003 REQ-004 SC-004 REQ-005 SC-005 REQ-006 SC-006 REQ-007 SC-007 REQ-008 SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T023

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T023 -->

## Task

Blocked by G0: also blocked by PR5 and the SPEC-052 v1 gate; re-check the v2 contracts, which are already written against the committed SPEC-052 v1 schemas (`schemaVersion`, `analysis.interactions`, the replaced `limits` and `unobserved` entries, the unchanged five phases and four-agent bound), against the then-current v1 schemas and the host-verification outcomes; finalize the migration note; obtain the reviewed SPEC-052 amendment that admits validated path tokens in agent prompts; and confirm the converter interface (bundled CLI subcommand `analyze-claude-transcripts`, used alongside the MCP tools under the constrained Bash that SPEC-052 REQ-016(d) defines plus that one subcommand as a planning amendment approved by the founder on 2026-10-24, folded into the analyze-phase agent, no new MCP tool). If no safe interface exists, record the transcript part of the gate as no-go, a valid negative result. Dependencies: T022; SPEC-052 PR2. Target files: `contracts/gate-result-v2.md`; `contracts/gate-result-v2.delta.schema.json`; `contracts/braid-gate-args-v2.delta.schema.json`; `plan.md`. Acceptance: every added, replaced and preserved v1 field, `assurance` constant and canonical limit is listed; the wording of SC-010 about v1 consumers is confirmed with the spec owner. Verification: both fragments overlaid on the real v1 schemas pass `Draft202012Validator.check_schema`, a v1 sample is accepted by v1 and rejected by v2, and a v2 sample is accepted by v2 and rejected by v1. Planned evidence: reconciled files and the composition check output. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009 REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T024

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T024 -->

## Task

Blocked by G0: Write the failing static and package tests first for the transcript inputs and the v2 result. Dependencies: T023. Target files: `tests/test_claude_transcript_gate_v2.py`; `tests/test_plugin_package.py`. Acceptance: tests cover transcript arguments, a `<transcriptDir>/subagents/` directory, none, and missing, unreadable, oversized and unrecognized files; they fail for the intended reason before implementation. Verification: `.venv-speckit/bin/python -m unittest tests.test_claude_transcript_gate_v2 -v`. Planned evidence: failing-run output. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009 REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T025

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T025 -->

## Task

Blocked by G0: Make `braid-gate` accept optional transcript paths or a `<transcriptDir>/subagents/` directory and have one agent convert them through the mapper CLI, receiving only aggregate output. Dependencies: T024. Target files: `integrations/agent-braid/plugin/workflows/braid-gate.js` (created by SPEC-052 PR2). Acceptance: the optional `transcripts`, `transcriptDir` and `republishPaths` arguments (path tokens only, never repository text) are validated before any agent is spawned, the conversion runs in the existing analyze-phase agent so the workflow still has at most four `agent(` call sites, the gate still spawns no worktree agents, edits nothing, merges nothing and starts no hook; no transcript content is placed in an agent prompt. Verification: static inspection tests. Planned evidence: test output. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T026

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T026 -->

## Task

Blocked by G0: Implement degrade-only handling: a missing, unreadable, oversized or unrecognized transcript changes only the transcript evidence and is reported with a fixed code, never the commit-level evidence. Dependencies: T025. Target files: `integrations/agent-braid/plugin/workflows/braid-gate.js`. Acceptance: no retry loop, no fabricated hazard or absence of hazard, commit-level labels byte-unchanged. Verification: degrade-matrix tests. Planned evidence: test output. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T027

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T027 -->

## Task

Blocked by G0: Implement result schema v2 and the script-computed merge: every pair keeps its commit-level label and gains the transcript hazards with coverage; the merge-tree baseline, replay eligibility and commit-level unknown share are unchanged in meaning; with no transcripts the v1 result is emitted unchanged. Dependencies: T025 T026. Target files: `integrations/agent-braid/plugin/workflows/braid-gate.js`; the v2 schema file. Acceptance: `executionAuthorization` false; `schemaVersion` `agent-braid-claude-gate-result/v0.2` only when transcripts were supplied; no pair is an independent candidate from transcripts; transcript paths appear only with `republishPaths`; v1 fields keep name, type and meaning. Verification: v2 schema tests and v1-consumer tests. Planned evidence: test output. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T028

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T028 -->

## Task

Blocked by G0: Rebuild and verify the plugin package: byte-stable inventory entry for the changed workflow, existing skills byte-identical, Codex manifest unchanged, rejection of missing, altered or extra files. Dependencies: T027. Target files: `scripts/build_native_plugin.py` (only if the inventory changes); `tests/test_plugin_package.py`. Acceptance: reproducible bytes; no version bump or publication. Verification: package build and verification tests. Planned evidence: inventory hash. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009 REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T029

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T029 -->

## Task

Blocked by G0: Update the recipe `docs/tooling/CLAUDE_WORKFLOWS.md` with the transcript inputs, what v2 returns and does not return, the migration note and the host-verification status of each unconfirmed behavior. Dependencies: T027. Target files: `docs/tooling/CLAUDE_WORKFLOWS.md` (created by SPEC-052). Acceptance: no speed, safety, conflict-freedom or semantic-correctness claim; transcript evidence described as requested calls with `partial` coverage. Verification: documentation review and structural gates. Planned evidence: file hash. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009 REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T030

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T030 -->

## Task

Blocked by G0: Founder: record native host receipts for the transcript path of the gate in a real Claude Code session: transcripts reachable and convertible, plugin MCP tools and plugin agents inside workflow agents, the Bash constraint (explicit launcher subcommands, never the launcher binary, including `analyze-claude-transcripts` alongside working MCP tools), nested workflow calls, and the Claude Code versions observed. Dependencies: T028. Target files: receipts named at PR6. Acceptance: unconfirmed behaviors stay labeled unconfirmed; an unavailable observation is recorded as unavailable, not as a pass; no extra spend. Verification: founder-run native observation. Planned evidence: receipt hashes. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T031

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T031 -->

## Task

Blocked by G0: Validate PR6 as a candidate: quick profile per increment, `--profile pr` once, re-snapshot, independent review, and obtained evidence only from commands that ran. Dependencies: T029 T030. Target files: `specs/053-claude-transcript-trace-adapter/assurance.json`. Acceptance: executed and pending checks reported separately; no release implied. Verification: `.venv-speckit/bin/python -m scripts.validate_spec_kit` and the profiles. Planned evidence: outputs and hashes. Obtained: none; human review pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009 REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T032

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T032 -->

## Task

Founder: decide the R2 release (plugin version after the R1 candidate `0.1.0-alpha.4`), release acceptance and any `plugin-dist` publication; no agent publishes, tags or releases. Dependencies: T031 and a recorded `g0-pass`. Target files: release records chosen by the founder. Acceptance: R2 includes the adapter and gate v2 only if G0 passed and host receipts support them; it states limits and makes no speed claim. Verification: release acceptance record. Planned evidence: record hash. Obtained: none; founder decision pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-009 SC-009 REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-053/T033

Proposed state: open. Parent: SPEC-053. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-053/T033 -->

## Task

Founder: close SPEC-053. Record the radar milestone review, technical review and founder closure, the disposition of SPEC-053 (implemented after `g0-pass`, or closed not adopted after `g0-fail`, or left blocked after `g0-inconclusive`), and confirm SPEC-023 acceptance is unchanged. Dependencies: T007 or T008 or T032. Target files: closure note; `research/adoption/2026-09-initial-triage.json` where the track state changes. Acceptance: negative and inconclusive outcomes are recorded without relabeling. Verification: `.venv-speckit/bin/python -m scripts.validate_spec_kit`. Planned evidence: closure record hash. Obtained: none; closure pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/053-claude-transcript-trace-adapter/assurance.json)
- Trace: REQ-001 SC-001 REQ-008 SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.
