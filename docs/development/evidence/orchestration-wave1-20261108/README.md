<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Orchestration wave 1 — prediction versus outcome (2026-11-08)

Derived, redacted receipt under [REAL_USE_EVIDENCE.md](../../REAL_USE_EVIDENCE.md).
It informs later planning; it grants nothing and proves nothing beyond its domain:
one orchestration session of the owner on this repository, six parallel tracks.

## Prediction

Agent Braid `analyze` (AIM input, exact-resource footprints, declared writes per
track) over the six wave-1 operations: **15 pairs, 15 `independent-candidate`, 0
`conflicting`, 0 `unknown`**. Candidates establish no concurrent-execution
refinement and no task correctness (analyzer limits).

## Outcome

| Observation | Result |
| --- | --- |
| File conflicts when the six PRs were brought up to date with `develop` | none (6 of 6 branch updates succeeded) |
| Merge order dependence | none observed (6 of 6 squash merges succeeded) |
| Failures that were not file conflicts | stale `current` evidence hashes inherited from `develop` (SPEC-066 receipt input `agent_braid/tooling_mcp.py`; SPEC-069 `procedure_013.json` inputs), one PR-local stale pin (SPEC-065 `spec.md`) |

The analyzer models resource footprints, not evidence-hash pins, so the stale-pin
class was outside its domain. Prediction and file-conflict outcome agree on this
sample (n = 6 operations); this does not estimate precision or recall.

## Tooling findings

1. `analyze-work` through the plugin MCP refused an AIM **envelope**
   (`analysisInputVersion`/`source`/`operations`) with a generic "bounded operation
   was refused" message. The same input is valid for the CLI `analyze`. The MCP accepts
   a single AIM record or a non-empty array of records (see issue #1080 on the schema
   description). The refusal text did not say so.
2. The array form succeeded for the wave-2 batch (3 operations, 3 independent
   candidates) and stored a 30-day private evidence copy.
3. The CLI `analyze` does not create System One shadow episodes; only successful
   plugin `analyze-work` calls do.

## Process findings

- Local `validate_spec_kit` fails in shared worktrees with "unreachable objects"; use a
  `git clone --no-local` for that check.
- One machine-wide full-suite slot made several tracks wait 35–40 minutes; CI on the
  PR head was the effective `pr` evidence.
- Track reports claimed review passes that were not all run; an explicit all-passes
  requirement was added to later briefs.
- Two develop-wide stale-evidence failures blocked every PR until M4.8 merged its own
  regeneration; a combined fix PR was not needed.

No identifiers, paths outside the repository, or credentials are recorded here.
