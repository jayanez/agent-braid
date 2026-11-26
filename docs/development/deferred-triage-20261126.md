<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Deferred milestone triage, 2026-11-26

Input for the tracking-sync phase (F5). It records verified facts and the owner's
decisions on the 72 open issues of GitHub milestone `Deferred` (#24, created
2026-10-31, [founder decisions](FOUNDER_DECISIONS_20261031.md)). Nothing on GitHub
was closed, moved, edited or commented on while this was written, and no spec,
`tasks.md` or `assurance.json` was edited. A decision here is a direction or
administrative decision, not a scientific finding, review or acceptance.

Evidence base: develop at `d42e778c`, read-only `gh api` on 2026-11-26, and the
repository files cited below.

## Result

| Outcome | Issues | Count |
|---|---|---|
| Close as not planned | #1410, #1411, #1413–#1417, #1419, #1473, #1424, #1343, #322, #326, #328 | 14 |
| Rescue into a refined open spec | #425 (SPEC-041 T008) | 1 |
| Keep in `Deferred` with a "Reopen when" | all others | 57 |

14 + 1 + 57 = 72, counted against the live milestone. The starting matrix listed 52
"keep" issues; the live milestone also holds the SPEC-041/043 parents and closure
tasks, and SPEC-033's three tasks moved from "keep" to "close" (Q4).

## Verified facts

1. **#1424 is still broken, and has drifted further.** `EXECUTABLE_SHA256` in
   `agent_braid/tooling_codex_observer.py:27` pins
   `0d5ac7aa…` (Codex `0.162.0-alpha.17.2`, from
   `specs/044-ai-tooling-evaluation/registration.draft.json:204`). The issue
   (2026-11-17) found `0.169.0-alpha.11.1`, sha `3ea20787…`. Today the same
   ChatGPT.app binary is `codex-cli 0.171.0-alpha.13.2`, sha-256
   `e1c3d034b7fd295d160d6ab412357f9c54241c8ed7a2a861f4730b8a4dd88ddb`
   (file dated 2026-11-26). `_verified_bytes` (line 88) would refuse it. Two
   self-updates in nine days confirm that an exact-hash pin cannot hold. No quota
   was consumed: only `--version` and a file hash were read.
   **No production code calls `CodexQuotaObserver`**; only
   `tests/test_tooling_codex_observer.py` does (search of `*.py`/`*.md`, outside
   evidence folders). HAR's cost gate (`agent_braid/harness_quota.py`) is pure and
   takes readings passed in; since owner decision 2026-11-21 (#1467, closed) those
   readings come from the orchestrator's agent-read of the desktop usage API. The
   issue's premise "HAR resumption depends on Codex quota" therefore does not
   depend on this module. SPEC-044 is cancelled, and no open spec owns the module.
2. **#1343 is mostly superseded; one gap remains unmeasured.** The issue's question 1
   (why HELD-04 fails) is answered by SPEC-078 D1 (`specs/078-lightning-heldout-v2/spec.md:90`):
   a guidance defect, fixed in T001, scorer unchanged. Question 3 (`final-no-schema`
   ablation) has no consumer. SPEC-079 (`specs/079-kind-choice-tool-fix/spec.md`)
   moves the fix to the tool surface and re-measures kind-choice on a fresh v4 split:
   REQ-006 (fresh held-out v4, no reuse of v2/v3 prompts), REQ-007 (Gate 0),
   REQ-008 (preregistered protocol and freeze), REQ-009 (one gate run of
   100 prompts × 3, owner-authorized), REQ-010 (a missed gate is a valid completion).
   Limits: its gate is SPEC-078 OD-1 (passing prompts, ≥ 2/3 valid first attempts;
   OD-B), not the literal SPEC-069 D4; its scope says "hosts other than
   `claude-code`" are out of scope. Codex (HELD-02, HELD-05, 7/10 prompts) and
   OpenCode validity are therefore **not measured by any open spec**. SPEC-079
   T008–T010 are open.
3. **SPEC-033 #322/#326/#328 are mostly absorbed by SPEC-066.** SPEC-066 already
   carries SPEC-033 T002/T003/T004/T006/T008 (#323–#325, #327, #329; they were moved
   to S1.5 by the `task_milestone_overrides` of SPEC-066 T003, and
   `specs/066-system-one-shadow/research.md` item 10 corrects the numbers) as
   T401–T403 (`tasks.md:394–441`), with the empty digest-pinned registry and atomic
   rollback to `off` shipped (T401, `agent_braid/system_one_promotion.py`), D7
   automatic rollback (T405), and the owner decision packet (T406). Covered:
   promotion criteria per decision point (REQ-401, spec.md:252) and rollback.
   **Not covered literally:** "bounded fallback chains" (T005) and "fresh
   reproduction" of an exact-candidate closure packet (T007). The owner accepted
   closing them with those two pieces recorded as not planned.
4. **F4a does not cover SPEC-043 T001/T003/T008.** `docs/README.md` and
   `docs/STATUS.md` do not mention the journey, onboarding or diagnostics tasks. What
   exists predates F4a: `examples/journey/run_journey.py` and
   `tests/test_journey_synthetic.py` (#1161: synthetic install → export journey with
   receipt and three negative controls; `evidence/sc-001.json` and the
   owner reopen decision still pending) and `docs/tooling/ONBOARDING.md` with
   `tests/test_onboarding_docs.py` (#1207: command-existence checks only; observed
   sessions in both hosts still required). Each issue body says so.
5. **Reopen criteria in the issue bodies.** Few bodies state one.
   - #1253 (SPEC-076 T001) lists "ADR 0042 accepted, local CUDA GPU, SPEC-075
     delivered". #771 (SPEC-060 T011) lists "every removal criterion … two
     published window releases and an owner removal decision".
   - SPEC-041/043 task bodies say "Reopen criteria are listed in that record":
     [owner decision 2026-10-31](../../specs/044-ai-tooling-evaluation/owner-decision-20261031-m45-closure.md),
     table "Deferred (not covered)". Current.
   - The System One bodies and the milestone description name only "SPEC-029 T001
     source permissions granted **and** admitted real groups > 0"
     ([FOUNDER_DECISIONS_20261031.md:29](FOUNDER_DECISIONS_20261031.md)). That is
     **stale**: SPEC-066 T101 (REQ-101) already admitted the owner's own work; T104
     (the owned corpus) is open; the 2026-11-14 B0 check was INFEASIBLE (3015
     labelled pairs, 4 System-2-`unknown`), so the learned model (S1.5d,
     T301–T303) is Deferred under the Wilson GO rule (D3).
   - #537, #551, #552 (SPEC-046), #760, and the other groups have no criterion in the
     body; criteria below come from the specs.
6. **Home specs.** Every kept or rescued item belongs to a spec refined on
   2026-11-26, except SPEC-046, which the owner deliberately left read-only (see
   `specs/046-native-ai-plugins` analysis note: draft authority snapshot
   `historical`, seven incoherences, SpecTorque 12/30). Closed specs (039, 044,
   049, 069, 070, 075) received no rescued work. **No home spec needs further
   SpecTorque refinement for F4.6.** SPEC-041 will gain T008's work as part of its
   existing, refined task list; no new spec is needed.

## Decisions and matrix

Owner answers are quoted as the options selected on 2026-11-26 (questionnaire in
Spanish; the labels below are the owner's chosen option text).

### Q1. Group A: SPEC-077 and #1473 — "Cerrar los 9 (Recomendado)"

| Issue | Decision | Reason |
|---|---|---|
| #1410 (SPEC-077 parent), #1411 T001, #1413 T003, #1414 T004, #1415 T005, #1416 T006, #1417 T007, #1419 T009 | **Close not planned** | SPEC-077 T008 (`evidence/t008-publication.json`, 2026-11-22) records "not published"; ADR 0043 is Rejected; T009 applies only if published; T001/T003–T007 were moved to Deferred by that decision. |
| #1473 (T014 drop reader jitter) | **Close not planned** | T014 finished 15/15; the issue itself says "Close if agent-read readings are not used again". |

Undo: reopen the issue; the design stays in `specs/077-harness-mcp-readonly/` and
ADR 0043.

### Q2. #1424 Codex quota observer — "Cerrar not-planned (Recomendado)"

**Close not planned.** No consumer exists (fact 1), SPEC-044 is cancelled, and an
exact-hash pin breaks on every self-update. The open decision of the issue
(A: re-pin by hand; B: code signature Team `2DC432GLL2` plus allow-listed version,
needs its own spec or ADR) is recorded here, not made. **Reopen when:** a production
consumer of `CodexQuotaObserver` is proposed in an open spec (the natural owner is
SPEC-084 T005 cost gate); that spec then decides A or B and the new transport copy.
Home spec for a fix: none today. Undo: reopen.

### Q3. #1343 analyze-work D4 — "Cerrar, superado por 079 (Recomendado)"

**Close not planned**, superseded by SPEC-078 D1 and SPEC-079. Recorded gap, no
issue: Codex 24/30 first-attempt valid (HELD-02, HELD-04, HELD-05) and OpenCode are
not re-measured. **Reopen when:** SPEC-079 T010 converges and the owner wants the
measurement extended to Codex/OpenCode on a new held-out set (the SPEC-069 set is
spent). Home spec if reopened: a new spec, not SPEC-069 (closed) and not SPEC-079
(Claude Code only). Undo: reopen.

### Q4. SPEC-033 #322, #326, #328 — "Cerrar los 3, absorbidos por 066 (Recomendado)"

**Close not planned**, absorbed by SPEC-066 T401–T406 (fact 3). Recorded as not
planned: bounded fallback chains; fresh reproduction of an exact-candidate closure
packet. Parent #321 stays open (Q8). Undo: reopen.

### Q5. SPEC-041 #418, #423, #425 — "T001/T006 parked, T008 rescate (Recomendado)"

| Issue | Decision |
|---|---|
| #418 T001, #423 T006 | **Keep.** Reopen when (2026-10-31 record): T001 — all five skills loaded at recorded versions, per `procedure_portable_bundle`; T006 — C1–C3 receipts for `evidence` on verified, failed and inconclusive records. |
| #425 T008 | **Rescue → SPEC-041 (refined 2026-11-26).** Build a synthetic adversarial-guidance control: untrusted text asking for grants, secrets or false success must be refused by deterministic checks and must not change skill guidance vs. permission enforcement (`procedure_adversarial_guidance`, `evidence/sc-008.json`). No native host needed. F5 decides the target milestone: milestone 19 (M4.5) is closed, so the owner/F5 must pick or reopen one. |

### Q6. Closure bookkeeping — "Mantener parked con trigger (Recomendado)"

#426 (SPEC-041 T009), #427 (T010), #448 (SPEC-043 T009), #449 (T010): **Keep.**
Reopen when: T001–T008 of the same spec are closed or closed by owner decision;
then run quick/PR gates, freeze the candidate and record the human decision.

### Q7. SPEC-043 #440, #442, #447 — "Parked con criterio del record (Recomendado)"

**Keep.** Reopen when (2026-10-31 record): T001 — one session or owned synthetic
journey covering install, analysis, plan, grant refusal, execute, verify, recovery
and export, with `evidence/sc-001.json` and a reopen decision (the synthetic runner
of #1161 exists); T003 — an observed `plan` session with `prepare`, the order and
the exact missing authority explained, then refused execution; T008 — onboarding,
diagnostics, raw-evidence access and rendering fallback shown in both hosts.

### Q8. Parents #417 (SPEC-041), #439 (SPEC-043), #321 (SPEC-033)

**Keep open.** Parents follow their children (2026-10-31 record). #321 stays until
SPEC-066 T403/T406 decide promotion; close it then.

### Q9. SPEC-046 — "Sí, solo lectura + parked (Recomendado)"

**Keep** #537, #551, #552; SPEC-046 stays read-only and is **not** refined in F4.6.
Reopen when: the owner decides to submit to OpenAI/Anthropic and the external
requirement is met (T014 partner eligibility; T015 executable/size exception and the
directory checklist). The seven incoherences stay in the analysis note, to be fixed
only if the owner authorizes a refinement later.

### Q10. System One — "Parked con trigger corregido (Recomendado)"

**Keep** parents #275, #284, #303, #312, #321 (see Q8), SPEC-030 #294–#302 and
#581–#588, SPEC-032 #314, #317, #318. **Reopen when:** (a) SPEC-029 T001 source
permissions are granted for third-party sources and admitted real groups > 0, **or**
(b) SPEC-066 T104 builds the owned corpus and the S1.5d Wilson GO rule gives GO for a
learned model (T301–T303). Replaces the single criterion of 2026-10-31.

### Q11. SPEC-076 — "Parked con trigger (Recomendado)"

**Keep** #1252–#1267. Reopen when: the founder accepts ADR 0042 through the go/no-go
of T001 (#1253, OD-1), a local CUDA GPU exists, and SPEC-075 is delivered (it is).

### Q12. SPEC-060 — "Parked con trigger y fecha (Recomendado)"

**Keep** #760, #771. Reopen when SPEC-060 REQ-007 holds: two published window
releases after the one carrying v0.2, release notes, a repository-reference search and
an owner removal decision under `agent-braid-tooling/v0.3`; review no later than
**2027-04-25**.

### Home spec for #1424 and #1343

Moot: both closed (Q2, Q3). No open or closed spec receives them; a future fix needs a
new or refined open spec, never SPEC-044, SPEC-069 or SPEC-049.

## Full matrix

| Issues | Spec | Decision | Reopen when / note |
|---|---|---|---|
| #1410, #1411, #1413, #1414, #1415, #1416, #1417, #1419 | 077 | close not planned | n/a (ADR 0043 Rejected) |
| #1473 | HAR T014 | close not planned | n/a |
| #1424 | 044 (cancelled) | close not planned | production consumer of the observer proposed (Q2) |
| #1343 | 069 (closed) | close not planned | SPEC-079 T010 converges and Codex/OpenCode extension wanted (Q3) |
| #322, #326, #328 | 033 | close not planned | absorbed by SPEC-066 T401–T406 (Q4) |
| #425 | 041 T008 | rescue → SPEC-041 | target milestone chosen in F5 (Q5) |
| #418, #423 | 041 | keep | Q5 criteria |
| #417 | 041 parent | keep | follows children |
| #426, #427, #448, #449 | 041/043 | keep | Q6 |
| #439 | 043 parent | keep | follows children |
| #440, #442, #447 | 043 | keep | Q7 |
| #537, #551, #552 | 046 | keep, spec read-only | Q9 |
| #275, #284, #303, #312, #321 | 028, 029, 031, 032, 033 parents | keep | Q10 (#321: Q8) |
| #294–#302, #581–#588 | 030 | keep | Q10 |
| #314, #317, #318 | 032 | keep | Q10 |
| #1252–#1267 | 076 | keep | Q11 |
| #760, #771 | 060 | keep | Q12 |

## Notes for F5

- Closure mechanism: `docs/development/GITHUB_TRACKING.md` says task state follows
  the `tasks.md` checkbox except for a documented override, and that
  `task_cancellations` (owner-adopted decision file with pinned hash,
  `state_reason=not_planned`) is the noncompletion disposition. The task issues in
  this list (#322, #326, #328 and the SPEC-077 tasks) have unchecked boxes, so
  closing them on GitHub alone would be reopened by the next sync. F5 must register
  them, and this file may serve as the decision record once frozen. The three
  non-task issues (#1343, #1424, #1473) and the SPEC-077 parent #1410 are outside
  that mechanism and need a direct close with state reason `not_planned`.
- The Deferred milestone stays open; 57 issues remain.
- Tracked specs still hold unchecked tasks for the closed issues; this triage did
  not edit them (the owner's rule for this phase).

## Milestone description draft

> Parked work with an explicit reopen condition; nothing here is accepted,
> cancelled by this milestone, or authorized. Created 2026-10-31 by founder
> decision ([record](https://github.com/jayanez/agent-braid/blob/develop/docs/development/FOUNDER_DECISIONS_20261031.md)); triaged
> 2026-11-26 ([record](https://github.com/jayanez/agent-braid/blob/develop/docs/development/deferred-triage-20261126.md)). Reopen
> conditions: **System One** (SPEC-028–033 parents, SPEC-030, SPEC-032): SPEC-029
> T001 third-party source permissions granted and admitted real groups > 0, or
> SPEC-066 T104 owned corpus plus an S1.5d Wilson GO for a learned model.
> **SPEC-076** (local GRPO): founder go/no-go accepting ADR 0042, a local CUDA GPU
> and SPEC-075 delivered. **SPEC-046** T014/T015: owner decision to submit and the
> external requirements met (spec read-only). **SPEC-060** T011: alias-removal
> criteria of REQ-007 and an owner decision, review by 2027-04-25. **SPEC-041 and
> SPEC-043** tasks: the observation criteria of the 2026-10-31 M4.5 record; T009/T010
> follow T001–T008. Task-level overrides to S1.5 for the SPEC-066-absorbed tasks
> still apply. Parent issues stay open.
