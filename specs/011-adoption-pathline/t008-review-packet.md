# SPEC-011 T008 — proportional validation and human review packet

**Prepared:** 2026-10-31 against `develop` at `6f4870ea8a885f3bf5c1e4e563a9a3759886d9aa`.
**Status:** preparation only. `assurance.json` keeps `human_review: pending`; T008
stays unchecked in `tasks.md`. Nothing here records, implies or infers a review
decision, an adoption or a stage transition. CI and this packet cannot approve the
registry.

## 1. Proportional validation (task requirement: `tasks.md` T008)

The change under review is governance metadata only (`research/adoption/`,
`specs/011-adoption-pathline/`). The profile is therefore the registry's own
validators plus the repository invariants; no provider SDK, network source or
clean-room run is in scope (spec limits).

| Check | Command | Result |
|---|---|---|
| Registry structure and pathline | `python3 scripts/validate_adoption_tracks.py` | passed: "structure and conservative pathline checks passed (no approval inferred)" |
| Positive and negative tests | `python3 -m unittest tests.test_adoption_pathline -v` | 8 tests, OK |
| Radar provenance | `python3 scripts/validate_research_radar.py` | passed (offline check only) |
| Repository invariants | `python3 scripts/validate_repository.py` | passed |
| Whitespace | `git diff --check` | clean |
| Independent-clone gate | `fresh-validate.sh <worktree> quick` and `pr` | recorded in the PR description (depends on the frozen branch tip) |

Manual structural observations on the committed registry
(`research/adoption/2026-09-initial-triage.json`, sha256
`df0cda9cf1fc08dbdcbf2b43098724d048b354596376acf43a8b4d41717fa216`, 7 tracks):

- No track is `adopted`; none has `obtainedEvidence` (all arrays empty).
- Every `affectedArtifacts` path exists (checked for all 7 tracks).
- Every track has an `owner` (`Agent Braid maintainer`, a role rather than a named person) and a `nextDecision`.
- AT-2026-004 has no `sourceRadarIds`; it carries a `sourceNote` instead.

Limits: structural checks do not verify source freshness, source accuracy, that
any capability delta is real, or that any hypothesis holds. They do not establish
adoption, superiority, adapter correctness or authority to execute.

## 2. What the reviewer is asked to decide

The registry is a draft until a human reviews the seeded dispositions
(`plan.md`, "Human review and unresolved decisions"). One decision per track,
recorded by the reviewer, not by an agent:

| Track | Stage / decision now | Current-stage actor, date | Reviewer decision needed |
|---|---|---|---|
| AT-2026-001 OpenAI approval evidence | `triaged` / `pending` | project preparation, 2026-09-23 | Confirm the seeded `triaged` disposition and next decision, or request changes. |
| AT-2026-002 MCP async state | `triaged` / `pending` | project preparation, 2026-09-23 | Same. |
| AT-2026-003 A2A conformance | `decision` / `watch` | project preparation, 2026-09-23 | Confirm the `watch` outcome (see flag A). |
| AT-2026-004 OpenTelemetry transport | `decision` / `watch` | project preparation, 2026-09-23 | Confirm the `watch` outcome (see flags A, B). |
| AT-2026-005 CoAgent comparator | `decision` / `research-only` | project preparation, 2026-09-23 | Confirm `research-only` (see flag A). |
| AT-2026-006 Claude dynamic workflows | `differentiation-hypothesis` / `pending` | project preparation; founder decision pending, 2026-10-23 | Confirm the stage record only; the hypothesis and G0 gate belong to SPEC-052/053. |
| AT-2026-007 Orchestrator coordination | `differentiation-hypothesis` / `pending` | project preparation; founder decision pending, 2026-10-24 | Confirm the stage record only; the hypothesis and G1 gate belong to SPEC-057 (with SPEC-058/059). |

## 3. Flags for the reviewer (observations, not findings of fact about intent)

- **A. Decision-stage entries were written by "project preparation".** Tracks 003,
  004 and 005 sit at stage `decision` with an `actor` of `project preparation`, not
  a named human. The pathline says stage transitions are human decisions
  (`spec.md`). Reviewer: say whether these three outcomes are accepted as your
  decisions, replaced, or sent back to `triaged`. Until you do, treat them as
  proposed dispositions.
- **B. AT-2026-004 has no radar signal.** Its history opens with a "weekly radar
  candidate" on 2026-09-23 without a committed `RAD-` ID, so its provenance is a
  free-text note. Reviewer: accept the note, or require a committed radar record.
- **C. "founder review" actor on `observed`.** Tracks 001–003 and 005 record the
  `observed` transition as `founder review` of
  `research/radar/2026-09-18-m0.5.json`. This packet does not verify that review;
  confirm it matches your recollection or amend.
- **D. The 2026-09 seed is historical.** Per
  `research/adoption/2026-10-foundation-followup.md`, current next work for 001–005
  lives in SPEC-023/025 and is a map, not an adoption record. Reviewing the seed
  does not review those later specs.
- **E. 006/007 carry kill criteria and gates owned elsewhere.** Approving their
  stage record does not approve SPEC-052/053/057/058/059, preregistration of G0/G1, or
  any wording implying uniqueness.

## 3a. Real-use receipt (2026-10-31)

Question: do any adoption claims in the registry touch actual usage? Answer: no.
No track is `adopted`, no track claims runtime use, and every `obtainedEvidence`
array is empty, so there is no usage claim to corroborate.

Local sources queried (read-only; counts only, no content committed):

| Source | Result |
|---|---|
| Telemetry (`agent-braid telemetry status`, default mode `off`) | 33 daily aggregate cells; scope is CLI `analyze`/`analyze-git` and portable MCP tool calls only, so it cannot observe adoption tracks |
| `~/.local/share/agent-braid/{evidence,coordination,identity}` | present; 171 files mention `AT-2026-001`…`007` as text; not examined as usage |
| `~/.local/state/agent-braid`, `~/Library/Application Support/AgentBraid` | 0 matches |
| `~/.codex/sessions` | 844 files, 0 matches |
| `~/.claude/projects/**/*.jsonl` | 122 files mention a track id as text; not examined as usage |

Observations: **no usage observations** of any adoption track. Text mentions are
development-time references, not evidence that a track was used or adopted. This
receipt informs the review and grants nothing.

## 4. Review outcome (to be completed by the human reviewer)

This section is intentionally blank. A review needs a repository `review_record`
before `assurance.json` may record `approved` (`docs/development/SPEC_KIT.md`,
assurance record). No such record exists yet.

| Item | Value |
|---|---|
| Reviewer name and role | _pending_ |
| Conflict-of-interest statement | _pending_ |
| Review date | _pending_ |
| Per-track decisions (001–007) | _pending_ |
| Overall: `approved` / `changes-requested` | _pending_ |
| Review record path | _pending_ |

After a decision exists, closing T008 needs its own PR that adds the review record,
updates `assurance.json` and checks T008. That PR is out of scope here.
