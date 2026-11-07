# Founder decisions — 2026-11-07

Successor of [FOUNDER_DECISIONS_20261101.md](FOUNDER_DECISIONS_20261101.md). This
record holds the owner's (jayanez, founder) decisions of 2026-11-07 on an automated
delivery wave for M4.8 (SPEC-069) and the S1.5a closure (SPEC-066). The owner gave
them interactively in an OpenCode planning session; each question offered options,
consequences and a recommendation. The transcript is not stored in the repository.
These are direction, scope and authorization decisions, not scientific findings,
reviews or acceptance.

## Context observed before the decisions

- Real-use telemetry on the owner machine (2026-10-16 to 2026-11-07, read under
  [REAL_USE_EVIDENCE.md](REAL_USE_EVIDENCE.md)): `analyze-work` through MCP had 32
  accepted and 15 refused calls. System One shadow recorded 24 episodes (139 pairs),
  all `abstained`. Observational, not preregistered.
- The local Spec Kit preflight fails in the shared object store of the main checkout
  (`public repository contains unreachable objects`); automated tracks use fresh full
  clones as [SPEC_KIT.md](SPEC_KIT.md) prescribes.
- The SPEC-069 P2 baseline (PR #1150, opened by a separate Claude Code session)
  reports a negative result against D4 in Claude Code and OpenCode; Codex was not run.

## Decisions

| # | Scope | Owner's answer | Recorded effect |
|---|---|---|---|
| 1 | Target | "M4.8 + cierre S1.5a" | The wave covers SPEC-069 P3 and the SPEC-066 S1.5a closure. HAR is out of scope. |
| 2 | SPEC-069 P3 | "Sí, P3 incondicional" | P3 (T005, T006, T008, T014) runs without waiting for further baselines. The D9 ablation arm still decides whether the per-kind schema is kept. The P2 baseline in PR #1150 also misses D4, so the D6 condition and ADR 0038 point 7 are met on their own terms; no ADR amendment is needed. |
| 3 | Split of SPEC-069 work | "Claude Code: T010/T013; oleada: P3 + S1.5a" | The Claude Code session keeps T013, T010 (baseline, Codex run and final run) and PR #1150. The wave owns T005, T006, T008, T014 and the T011 draft. |
| 4 | SPEC-066 T031 | "Spec al código" | REQ-003 is aligned with the shipped code: an episode is recorded for report-bearing `analyze` and `analyze-work` results. No behaviour change. |
| 5 | GitHub authority | "Merge y tracking acotado" | Wave agents may squash-merge their own pull requests into `develop` once the `validate` aggregate passes on the exact head commit, and may run `sync_github_tracking.py audit`/`apply` scoped to milestones 28 and 26 with the reviewed digest. No tags, releases or `plugin-dist` pushes by the wave; #1080 stays open until REQ-012. |
| 6 | Branch protection | "Sí, marcar validate" | `validate` becomes a required status check on `develop`; the other protection settings are unchanged. |
| 7 | Stale worktree | "Recuperar en T5" | The uncommitted S1.5 documentation edits of the local `claude/s15-docs-readme` worktree are compared with `develop` and salvaged where still valid; the original worktree is left untouched. |
| 8 | Parallelism | "3 a la vez" | At most three implementation tracks run at once; merges are serialized; at most one local `quick` profile at a time and no local `pr` profile. |
| 9 | Native-run credentials | "Llavero de macOS"; "Añado ANTHROPIC_API_KEY al llavero" | Native drivers read `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` from the macOS keychain (services `agent-braid-openai`, `agent-braid-anthropic`) at run time and inject them into the sandboxed host only (D13, A10). |
| 10 | Native-run spend | "Tope de EUR 25 por pasada" | Each native pass stops automatically when its estimated or counted cost reaches EUR 25. |
| 11 | Pinned models (D9) | "Los modelos por defecto de cada host" | Each host's default model identifier is recorded at the start and pinned for the baseline and the final run. |
| 12 | Release | "sí al release 0.1.0-alpha.8" | The owner's explicit yes for SPEC-069 T012. It applies only when REQ-010 meets D4 in Claude Code, Codex and OpenCode (D11) and the published package matches the reviewed candidate (SC-012). A missed or unobserved host still blocks the release; the yes does not reinterpret the gate. |

## Not decided here

Human review of SPEC-066 S1.5a (T032), the S1.5b start, any HAR decision, and any
change to the D4 threshold remain separate owner decisions. Reviews run by
automated agents are not independent Luna review and do not grant approval.
