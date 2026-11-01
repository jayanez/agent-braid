# System One completeness audit — 2026-11-01

Adversarial and counterfactual review of System One (SPEC-028–033, milestones
S1.0–S1.4) on `develop` at `6f2e795c`. The owner asked whether the layer-1
decision feature is actually incorporated and in use, after all S1.x milestones
were closed on 2026-10-31. Conducted by a Claude Code session, with read-only
subagents covering the specifications, the source code and the GitHub tracking.
It is a review record, not a human or scientific acceptance.

## Verdict

System One is incomplete and unused. The milestones closed by an administrative
decision ([2026-10-31 decision 3](../../../development/FOUNDER_DECISIONS_20261031.md),
"Cerrar como diferido"), not because the feature was finished. What was
delivered is deterministic engineering over synthetic fixtures. No product path
calls it.

## Findings

1. **Closed is not delivered.** All 45 issues left in S1.0–S1.4 are closed as
   `COMPLETED`:
   - About 22 have code: PR #334 (SPEC-028 core), PR #373 (SPEC-031/032 advisory
     layer) and PR #655 (verified typed-plan core, DDP-T02–T07).
   - About 23 closed on documents or historical records only. The 15 SPEC-029
     issues T010–T024 were each created and closed within about 3 seconds,
     without comments. DDP-T01 and DDP-T08 closed on documents.
   - S1.2 (native model) closed with zero delivered issues.
   - Review tasks (SPEC-028 T008, SPEC-031 T001, SPEC-032 T008) are checked
     without a recorded review.
   - 43 S1 issues are open in milestone `Deferred` (#24), including the six spec
     parents. The 88 issues match the 88 S1 Project items.
2. **Code without product callers.**
   - About 4,360 lines (`agent_braid/system_one*.py`, `mcp_advice.py`) and about
     4,770 lines of tests are on `develop`.
   - The only user entry point is the opt-in `agent-braid system-one` command
     (`cli.py`), over synthetic fixtures.
   - `analysis.analyze_with_advice`,
     `structured_exchange.verify_candidates_with_advice` and
     `runtime_scheduler.select_ready_rank_hint` have no source callers.
   - The eight `system_one_verified_*` modules are imported only by tests.
   - The plugin MCP tools and plugin skills do not reference System One.
3. **No learned model.** `BACKEND_ID` is `stdlib-rule-fixture-v1`, calibration is
   the constant `absent`, and the strict policy always abstains. SPEC-030 has 0
   of 16 tasks done, and the repository holds no model weights.
4. **Use cannot be observed.** Telemetry has no System One operation, and the
   `system-one` command returns before the `observe` wrapper.
5. **Experiments concluded as engineering, not as science.** There are 21 studies
   ([evolution](../../evolution.md), [register](../../evidence-register.json)),
   run mostly by the Codex coordinator.
   - Most were negative: the neural workflow took 16.6 s against FIFO's 7.2 s;
     the Laya reference scored about 32–34% with no transfer gain; option
     grounding made results worse; the T016 gain came from policy, not weights.
   - The positive results are bounded: a taxonomy task (86% EN / 81% ES), and a
     verifier with 100% admitted accuracy inside a finite synthetic grammar of
     2–4 operations, with 57–75% action coverage.
   - The registered comparison (SPEC-029 T009) never ran. Every study keeps
     `humanAcceptance: pending`.
6. **Blocked without an owner.** The reopen condition depends on RF-T03, RF-T04
   and RF-T05 (store, observer, source admission), which are deliberately
   unassigned.
7. **Stale documentation.** README and RESUMPTION still describe open milestones
   and local Codex checkouts. The code reached `develop` in PR #655. SPEC-051 and
   ADR 0026 are published, although the corpus calls them unpublished.

## Real-use evidence (derived receipt)

Queried on 2026-11-01 under [REAL_USE_EVIDENCE](../../../development/REAL_USE_EVIDENCE.md):

- **Local telemetry** (`metrics.sqlite3`) has 44 product calls within its 30-day
  retention: CLI `analyze` 4, `analyze-git` 8; MCP `analyze` 2, `analyze-work` 24,
  `prepare` 2, `execute` 2. System One is not observable there.
- **Claude Code and Codex transcripts** contain zero invocations of
  `agent-braid system-one`, `s1_advise_stage` or `agent_braid_verified_prepare`.
  The only match is this audit session.

The product is used, but System One is not.

## Counterfactuals

- **Deleting System One** would change no user-visible behaviour.
- **Wiring it in advise mode today** would add little. The deterministic analyzer
  (System 2) is exact and cheap, so learning to repeat it has no value. The
  verifier covers only a synthetic grammar.
- **Granting corpus permissions at the start** would not have unblocked SPEC-029.
  Its rubric required blind labelling by two human reviewers, which a
  one-person project cannot supply. The design was infeasible for the real
  context, not just unfinished.
- **The path not taken:** System One earns its cost only where System 2 is
  undetermined, which means pairs classified `unknown`. The ground truth for
  those pairs arrives later, as observed outcomes in the owner's own runs. Those
  runs are already recorded by SPEC-047, SPEC-053 and SPEC-059.

## Outcome

The owner chose to resume in shadow mode with owned data and to adopt the
strongest Laya and Jev capabilities
([decision](../../../development/FOUNDER_DECISIONS_20261101.md)). The work is
[SPEC-066](../../../../specs/066-system-one-shadow/spec.md), track S1.5, under
[ADR 0034](../../../adr/0034-system-one-shadow-advisory-boundary.md).
