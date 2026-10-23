# Founder decision record: G0 budget, transcript source rights and SPEC-052 amendments

**Date:** 2026-10-24
**Decider:** Juan Antonio Yáñez García (founder), recorded from the founder's
explicit answers in the delivery session; this file records those answers and
does not itself create authority beyond them.

## 1. G0 budget and transcript source rights — signed

The founder signs the draft
[budget and source decision](budget-and-source-decision.md) without amendments:

- G0 runs on the founder's existing Claude subscription with included quota and
  **EUR 0 additional spend**; no API key, paid call, credit, overage,
  auto-recharge or upgrade.
- The founder's own Claude Code subagent transcripts, from the founder's own
  sessions on an owner-controlled repository, may be read locally as measurement
  input under that record's retention rules (probe output is integer counts
  only; nothing is copied into the project repository or published).
- The founder confirms that this local use of the founder's own session files is
  consistent with the provider terms applicable to the account. This is an
  owner declaration, not an authenticated observation.

Still required before the first G0 run, and not implied here: the founder's
manual declaration that extra usage and auto-recharge are off, an explicit freeze
of the preregistration (planned after PR1 is merged, on the merged commit), and
each run's own host approval. This record authorizes no workflow run by a coding
agent.

Bound bytes (SHA-256 at signature):

| File | SHA-256 |
|---|---|
| `specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md` | `333406c25dbdf87b0cd72c2895f441998710e7f3a477e95c137647e12e4a9c62` |
| `docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md` | `02291d0d9cbde74222652ba6b22a4cdd0293fcf7a5aa3c6adf9a119cb6cb3e8d` |
| `docs/experiments/claude-workflow-g0-inputs.json` | `6a5b6167257523947361be3ecba26690a42b5d1316d9045c664f2f71ec628033` |

If review changes any bound file before the freeze, this signature is stale and
must be renewed against the new bytes; it is never silently carried over.

## 2. SPEC-052 planning amendments — approved

The founder approves, as planning amendments only:

1. `plugin workspaces` (no further arguments) in the constrained-CLI fallback
   allowlist of gate v1, for the registry refusal rules.
2. `analyze-claude-transcripts` as the one additional explicit launcher
   subcommand for gate v2, usable alongside working MCP tools; it remains
   blocked by G0 and by host verification of the Bash constraint.
3. Validated path tokens (transcript paths checked by the script) in gate v2
   prompts, in addition to identifiers.

These approvals do not accept any capability, adopt the ADR 0024 amendment,
approve the specifications' human review or authorize execution, grants,
merges, releases or remote publication.

## 3. Sequencing decisions recorded

- PR1 push and pull request: authorized.
- G0 freeze: after PR1 is merged.
- Human review of SPEC-052/053: recorded after the founder reviews PR1, scoped to
  planning.
- Remote publication: after merge, scoped to M4.6 only, with a
  `delivery/publication.json` receipt; other pending operations are excluded.
- PR2 (SPEC-052 implementation): may start on a branch stacked on PR1, with no
  version bump or release.

`executionAuthorization` remains `false`.
