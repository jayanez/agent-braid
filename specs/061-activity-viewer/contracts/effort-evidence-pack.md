# Effort evidence pack (draft contract `agent-braid-loom-effort-pack/v0.1`)

Produced only by `agent-braid view export --from FILE --to PATH --include-effort
--baseline NAME --arm NAME=FILE ... --arm-note NAME=TEXT ...`. Purpose: let an owner show, at work, how
recorded sessions with and without Agent Braid compare in host-estimated effort,
without turning estimates into claims.

## Inputs

Each arm is a loom file recorded with `serve --record FILE --record-effort` (or a
replay file with effort events). At least two and at most 8 arms; one is named the
baseline. Each arm has a selection note (`--arm-note NAME=TEXT`, at most 256
characters) that says how the session was chosen. Unless the owner records a
matching (same task, repository state and host version) in the note, the pack
states that the arms are unmatched.

## Files

| File | Content |
|---|---|
| `manifest.json` | `schemaVersion`, generator version, arms with selection notes and matching status, baseline, file hashes, labels, non-claim statement |
| `loom.jsonl` | events of the `--from` file (paths relative) |
| `effort.jsonl` | one row per arm, strand and phase: tokens by type, cost, coarse duration bucket, `basis: host-estimate` |
| `comparison.json` | one comparison per non-baseline arm: `left` = baseline, `right` = arm, `differences` of `{field, left, right}` for every differing field (a field absent from one arm has `null` on that side), `identical`, `unlistedChange` |
| `summary.md` | per-arm totals, event counters, gaps, labels, selection notes and the non-claim statement |
| `index.html`, `braid.svg` | static rendering, no script element, no remote URL |

The comparison follows `agent-braid harness compare`: `differences` rows carry
only `field`, `left` and `right`, absent fields are `null`, and `identical` and
`unlistedChange` are comparison-level fields. The only addition is the arm
metadata in `manifest.json`.

## Labels and non-claims

Every effort figure carries `basis: host-estimate` and `evidence: empirical`, and no
compatibility class (effort is not an analysis result). `summary.md` and
`manifest.json` contain this statement:

> These figures are host-reported estimates from the recorded sessions. They are
> not a measurement of speedup, cost saving or causal effect, and they do not
> generalize beyond these sessions.

Subagent effort that a host does not attribute appears as a
`subagent-usage-unattributed` gap, never as zero. Fields missing from an arm are
`null`, never zero.

## Privacy

Identifiers stay salted per original session; the pack contains no prompts, tool
inputs or outputs, file content, absolute paths or absolute timestamps. Durations
are bucketed (`<1s`, `1–10s`, `10–60s`, `1–10min`, `>10min`).

## Relation to Braid Harness

The pack reuses the comparison shape only. Registering it as a harness record kind
or feeding it into SPEC-049 evaluation is a HAR decision outside VIS.1.
