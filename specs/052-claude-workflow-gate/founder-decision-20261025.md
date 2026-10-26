# SPEC-052 founder decision: R1 allowlist on the MCP path

- **Date:** 2026-10-25. **Decider:** Juan Antonio Yáñez García.
- **Decision:** accept option A. The MCP path of `braid-gate` may ship in R1 with
  wildcard-tail Bash rules over the fixed hardened Git prefix, one command per Bash
  call, and `/tmp` as an allowed directory for the scratch cleanup.
- **Scope:** this accepts the allowlist trade-off found by HV-5 only. It is not a
  release decision, not adoption of ADR 0029 and not Agent Braid authority;
  `executionAuthorization` stays `false`. Release acceptance and the version number
  remain separate founder decisions.

## What is accepted

- One rule per permitted Git subcommand (`version`, `rev-parse`, `rev-list`,
  `cat-file`, `merge-base`, `for-each-ref`, `count-objects`, `hash-object`, and for
  the baseline `init` and `merge-tree` with the scratch prefix), each with the full
  hardened prefix and a trailing `*` for its arguments. The prefix and the set of
  subcommands stay fixed; the arguments of a named subcommand are no longer fixed.
- `mktemp -d /tmp/braid-gate.*` and `rm -rf -- /tmp/braid-gate.*`, with `/tmp` as an
  additional allowed directory. The script accepts only `/tmp/braid-gate.` plus eight
  alphanumeric characters (or its `/private` form).
- Without `/tmp` the cleanup is `refused` or `failed` and the run is capped at
  `ok-analyzed`, never `ok-certified`.
- The spec amendment of 2026-10-25 and `docs/tooling/CLAUDE_WORKFLOWS.md` already
  state this; no gate script change follows from the decision.

## Evidence

- `evidence/hv-5.json`: exact literal rules do not match commands with quoted
  arguments or grouped commands; a trailing wildcard matches; fail-safe under a
  strict allowlist.
- `evidence/native-gate-runs.json` (T030): `ok-certified` with wildcard-tail rules
  and `--add-dir /tmp` on two- and four-operation fixtures, `ok-analyzed` above four
  operations (stated limit), `hazards-found` on a same-line conflict.
- `evidence/auto-and-disabled.json` (T031): `ok-certified` in auto mode with no
  permission denials; with workflows disabled the gate is `unavailable`, not clean.

## Trade-offs considered

| Option | Gain | Cost |
|---|---|---|
| **A. Wildcard tails plus `/tmp` (accepted)** | Observed working in default and auto modes; no gate change; the tool surface stays host-enforced. | Rules wider than the literal REQ-016(b) text: any arguments of a named read-only subcommand; the agent can write under `/tmp`. |
| B. Change the commands | Literal rules again, narrowest surface. | Reopens script and prompts; T030/T031 to repeat; not shown to suffice. |
| C. Auto mode only | No wider rules. | Depends on a host mode, not on the allowlist; other modes unobserved. |
| D. Documentation recipe only | Cheapest. | REQ-016 becomes advice, not a control. |

## Residual risks and limits

- Wildcard tails let a misbehaving agent pass other arguments to the permitted
  subcommands (for example `rev-parse` or `cat-file` options); `init` and
  `merge-tree` only run under the scratch prefix. The script still validates every
  value it consumes, and no rule names a writing subcommand against the repository.
- Unobserved: manual interactive prompts, accept-edits mode, per-agent permission
  separation, launcher fallback rules, a managed organization policy, and the
  `disableWorkflows` key name against host documentation.
- A Claude Code release may change rule matching; the gate fails safe
  (`inconclusive` or `unavailable`) rather than unsafe.
