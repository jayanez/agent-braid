# SPEC-049 T004 native pilot admission packet (finalized 2026-11-20)

Status: **finalized. The owner admitted the pilot on 2026-11-20** with the answer "Admit
(Recommended)", given in the HAR sessions. The decision is recorded in
[`t004-admission-20261120.json`](t004-admission-20261120.json) (sha256
`7a1b1a5a18949f54bad47e1805760f1bf917d7b339ae2550eebc1fa17c1d83f3`).
`scripts/har_t014_cohort.py` pins that record by path and SHA-256. This packet and the
records admit only the SPEC-049/T014 native cohort, under the terms below.
`executionAuthorization` stays false: every unit still needs the root launcher, the
owner's `run` and a usage reading taken at most 5 minutes before the unit.

The 2026-11-16 draft of this packet listed items 1–4 as pending. Each one is now filled
from a committed record and its hash.

## What T004 had to decide

T004 says: "Admit a separate native pilot only after qualified host and source gates."

| # | Item | Record (sha256) | State 2026-11-20 |
|---|---|---|---|
| 1 | **Exact source** | `evidence/registration/t005-units-freeze-20261112.json` (`469135c420a01a5b56dbf49529f6a822c8b6469ef0d8ed9cbc8a95c5920bd934`); roster freeze `t005-roster-founder-freeze-20261030.json` (`499fe88d8bda05a500dcef2cb07e55429aad3ff59c5a0f2aefe2e9f9887741ff`); roster draft `t005-roster-draft.json` (`5056b3bbfafa4a667350ac823861a14d28ea232d5b901ea7bc93574dc721ff43`) | **Decided.** Option Q2 (a): the frozen T005 roster replayed natively. Holdout L1-C01-a, L1-C02-a, L1-C03-a, L1-C03-b, L1-C03-c. The cases are repository-owned synthetic and constructed tasks with one lineage (L1), so the result is descriptive only under D3 |
| 2 | **Candidate** | Arms A `4f53cda1…b945` and B `4bc36ca0…6516` (roster freeze R5/R6). Arm C `6674a8da7aab284f456a9cefd551ebddbb6546873a809ad6a3db48fedca1f7d9`, frozen in `evidence/registration/t014-terms-20261120.json` (`ef68417637be2c5b881ce95227eb0943ad4fedd98bb5498d1506b910612c68f1`) | **Decided.** Arm C was registered by the owner answer "Register it (Recommended)". It resumes from the checkpoint and does nothing else. It was selected offline on synthetic-control probes and is evaluated natively. Arm D is infeasible in this window |
| 3 | **Containment** | SPEC-065 `issuance-2026-11-17.json` (`33f89889bb7936d9715fdcb3f8e98d699849ebf720cfe60be2233673982d50c8`); containment `5a9f05c6…00df`, host `f2f65ae0…7f9d`, environment `600ba86d…c556` | **Decided.** Valid until 2026-12-17T22:19:29Z |
| 4 | **Host and model route** | SPEC-048/T008 verdict T008-11, `specs/048-harness-variant-laboratory/evidence/founder-decisions-20261120.json` (`854272506d8371fd711f7f791e82d4efbb6f0e57f0404262177116f2fa4464eb`). The host-profile decisions for T014 are in `evidence/registration/t014-profile-decisions-20261120.json` (`36149af6808b1f71bc869e2d4bddc53002c12cca44e45d40680bf13ae2675806`) | **Decided.** Claude profile qualified with limits. The route is Claude, Haiku and the subscription. Codex is refused |
| 5 | **Cash envelope** | `evidence/registration/d2-caps-founder-decision-20261031.json` (`b1851e1c…2d88`); per-cohort scope `d2-caps-scope-founder-decision-20261117.json` (`9e83093d…24cd`) | **Decided.** EUR 0 within the D2 caps: at most 30 min per unit, at most 10 % of the 5-hour window per session, at most 15 % of the weekly window per cohort, at most 16 units per cohort. SPEC-048/T008 units do not count toward the 16 |

## Owner answers, 2026-11-20 (given in the HAR sessions)

1. **T004 admission:** "Admit (Recommended)". The terms are items 1–5 above.
2. **T014 plan:** "P2, arm D infeasible (Recommended)". Arm C comes frozen from the offline
   round, and the cohort is 5 holdout cases × A/B/C = 15 units. The cap is 16 per cohort.
3. **Arm-C freeze:** "Register it (Recommended)". This freezes candidate `6674a8da…f7d9`.
4. **T012-03 for T014:** "Accept", with the order "Cuadrado latino R9 (Recomendado)". The
   config dir is not purged between units. The driver's registered Latin-square order
   (`slots()`) is used unchanged; it interleaves the arms and counterbalances A/B/C. The
   units are therefore not independent, and no cross-unit independence is claimed.
5. **Window:** "Hasta la caducidad (Recomendado)". The window runs from 2026-11-20 to
   2026-12-17T22:19:29Z, the issuance expiry.

## Limits carried from SPEC-048/T008 (founder T008-11)

- The units are not isolated from each other (T012-03), so no cross-unit independence is
  claimed.
- No claim is made about effort level (T012-07).
- The Codex profile stays refused. A partial host qualification does not imply that both
  hosts qualify.
- Only Haiku on the subscription route, at EUR 0, bound to the issuance-2026-11-17 records.

## Order of gates

1. SPEC-065 re-qualification and its issuance: **done** (2026-11-17).
2. SPEC-048/T008 units and the Claude profile verdict: **done** (T008-11, 2026-11-20).
3. The arm-C freeze: **done** (2026-11-20, T014 terms record).
4. The native source, with its rights and yield, registered before any outcome: **done**
   (option (a), the frozen T005 roster).
5. This packet finalized, with the owner's approval of source, route and cash: **done**
   (2026-11-20). The usage reading is still taken at most 5 minutes before each unit.
6. SPEC-049/T014 runs next, inside the window. The T014 launcher and installer are not
   installed on the lab machine yet. Each unit also needs the owner's `run`.

## Infeasibility path

If the cohort cannot run before 2026-12-17T22:19:29Z, T014 records that no native capture
happened, keeps its native branch pending as `tasks.md` requires, and names the item that
failed. No item may be filled from a double, a fixture or an estimate.
