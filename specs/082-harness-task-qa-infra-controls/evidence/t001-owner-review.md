# SPEC-082 T001: owner review (2026-11-23)

The owner (Juan Antonio Yáñez García, founder) reviewed `spec.md` and `plan.md` interactively, as merged in #1515 (`f0793dfd`) and current on develop. The answers below are the options the owner selected, quoted verbatim.

This review settles only the open decisions. It authorizes no code, no run and no execution (`executionAuthorization` false).

| Decision | Answer | Meaning |
|---|---|---|
| OD-1 Corpus size | "Construir ~30, congelar 20–50 (Recomendado)" | Build about 30 candidate tasks and freeze those that pass QA, keeping the corpus between 20 and 50. If fewer than 20 pass, that is recorded as a feasibility result. |
| OD-2 Lineage and stratum | "Fusión conservadora (Recomendado)" | Tasks share a lineage when they share a PR, a spec, a fixture base or an unresolved relation. There are three strata (continuity, coordination, repair), and they are never pooled. |
| OD-3 Private split storage | "Fuera del repo, hashes dentro (Recomendado)" | The private split lives in a local private store outside the repository, as ADR 0018 prescribes. Only its hashes are committed. The owner keeps a backup. |
| OD-4 Second reviewer | "Cruzada Claude↔Codex + tú (Recomendado)" | A new option (d), chosen after the owner asked for it. Details below. |
| OD-5 Infra policy | "2 reintentos, 10 % invalida (Recomendado)" | A trial may be rerun at most twice. A job is `invalid` if more than 10 % of its trials are infra errors, or if a task loses all its trials. The rule is frozen before any data exists. |
| OD-6 Exploit-agent venue | "En SPEC-084, si no queda incompleto (Recomendado)" | The exploit agent runs in SPEC-084 once its gates pass. If SPEC-084 is infeasible, the task stays `qa-incomplete`. The deterministic checks (the reference fix passes, a no-op fails) run locally before that, with no model. |
| OD-7 Split proportions | "40/40/20 por linaje (Recomendado)" | 40 % discovery, 40 % holdout and 20 % private holdout, assigned by whole lineage. |

**OD-4 in detail: cross adversarial review between Claude and Codex, with owner adjudication.**

Each task goes through three steps:

1. **Blind review.** Claude, in a Claude Code subagent, and Codex, via `codex exec -s read-only` pinned to the corpus commit, each try to break the task without seeing the other's work. They look for an ambiguous statement, a test that passes without solving the task (for example by deleting the test), a solution leak, or an oracle that does not check the outcome.
2. **Cross critique.** Each model critiques the other's report.
3. **Adjudication.** The owner settles every disagreement in an adjudication record.

How this meets REQ-008:
- The two model reviews are the two distinct review records REQ-008 requires. Both are labeled `model`, with model and version.
- The owner's adjudication is labeled `human`.

Limits:
- This is a recorded departure from Terminal-Bench 2.0, which uses two human auditors.
- Two model families from different vendors reduce shared blind spots but do not remove them.

Overall limits:
- The owner decides as owner, not as an independent reviewer.
- T002 (the Codex review of this spec) has not run yet. Any confirmed finding may reopen a decision through a dated amendment.
