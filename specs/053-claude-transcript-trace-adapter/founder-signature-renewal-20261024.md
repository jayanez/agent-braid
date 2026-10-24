# Founder declaration renewal: G0 budget and transcript source rights (revision 2)

**Date:** 2026-10-24
**Decider:** Juan Antonio Yáñez García (founder), recorded from the founder's explicit answers in the delivery session. This file is an agent-recorded transcription of those chat answers. It is not a cryptographic signature and it freezes nothing.

## Declaration (renewed against revision 2)

In answer to an explicit question that listed the file hashes below, the founder declared:

- G0 runs on the founder's existing Claude subscription with included quota and **EUR 0 additional spend**; no API key, paid call, credit, overage, auto-recharge or upgrade.
- The founder's own Claude Code subagent transcripts, from the founder's own sessions, may be read locally as measurement input with aggregate-only output under the retention rules of [budget-and-source-decision.md](budget-and-source-decision.md).
- The founder confirms that this local use of the founder's own session files is consistent with the provider terms applicable to the account (an owner declaration, not an authenticated observation).
- The founder declares that extra usage and auto-recharge are off (a manual declaration, not verified by any tool).

This renews the declaration of [founder-decision-20261024.md](founder-decision-20261024.md) section 1, which applied to the bytes of revision 1 and was superseded.

## Bytes this declaration applies to (revision 2, `develop` at `4934284`)

| File | SHA-256 |
|---|---|
| `specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md` | `53775c0de293b9db20a994d2283206f7db8e576c12c7bfc8d7959b6b0f6db138` |
| `docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md` | `066ea12b226410b52ac9843d14f57a257db3ea28d6a649b08336dc9318b788fd` |
| `docs/experiments/claude-workflow-g0-inputs.json` | `dd48f0adb47fee62da4c805c701b89e2beb1a32105ea2e9640e95e2b49a36625` |
| `docs/experiments/claude-workflow-g0-decision-vectors.json` | `c100a7acbd4a5a231f36967073c6d8e6169f76d97340647e49e8a85d6baedf55` |

If any of these bytes changes, this renewal is stale and must be renewed again; it is never silently carried over.

## What this does not do

- It does not freeze the preregistration. The freeze order in the inputs file still requires the layout census, a probe tested on a de-identified real fixture, the planned run count and yield estimate, the probe and runner hashes, and the founder's acceptance of the power operating point before the freeze decision.
- It authorizes no workflow run by a coding agent. The founder runs every G0 workflow; each run needs the host's own approval.
- `executionAuthorization` remains `false`.
