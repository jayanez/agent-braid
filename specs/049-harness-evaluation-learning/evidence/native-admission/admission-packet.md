# SPEC-049 T004 native pilot admission packet (DRAFT, 2026-11-16)

Status: **draft, prose only. It admits nothing.** The HAR wave-1 orchestrator prepared it. The
native-chain session finalizes it once the SPEC-048/T008 verdict exists, by the split agreed on
2026-11-16. Until then every row marked *pending* stays pending. A missing native route ends as
an infeasibility record, never as synthetic evidence. `executionAuthorization` is false.

## What T004 must decide

T004 says: "Admit a separate native pilot only after qualified host and source gates." Its
acceptance has five parts. Each one must be verified exactly, and each verification must be
recorded with its hash or reading:

| # | Item | Source of truth | State 2026-11-16 |
|---|---|---|---|
| 1 | **Exact source**: the native task source, its rights and yield | `corpus.md`; `evaluation-protocol.md` D1/D3 ("Observed native yield: 0") | *pending.* No permissioned native source is registered. See question Q2 |
| 2 | **Candidate**: the profiles of arms A–D and the arm-C refinement decision | `evidence/registration/t005-units-freeze-20261112.json`; `tests/harness_t014_arm_c.py` (#1382); the arm-C freeze needs a founder decision | *pending.* The arm-C freeze is not yet decided (track E prepares it) |
| 3 | **Containment**: a current SPEC-065 issuance | `specs/065-native-claude-containment/evidence/qualification/issuance-*.json` | *pending.* `fix/065-claude-system-events` voids the 2026-11-14 issuance, and a re-qualification follows |
| 4 | **Host and model route**: the Claude profile verdict, model, subscription route | SPEC-048/T008 `evidence/t008.json` and the founder verdict | *pending.* No completed unit yet. 0 units remain under T008-8, so a new founder decision is needed |
| 5 | **Cash envelope** | `evidence/registration/d2-caps-founder-decision-20261031.json` (D2) | **Known.** Additional cash is EUR 0. At most 30 min per unit, at most 10 % of the 5-hour window per session, at most 15 % of the weekly window for the whole cohort, at most 16 units, and a stop when weekly usage passes 80 %, when extra usage is on, or when the reading is stale |

## Order of gates (none can be skipped)

1. SPEC-065 re-qualification and its issuance (native-chain session; owner `run`).
2. SPEC-048/T008: a new founder decision on units, then at least one completed unit within the
   caps, then the founder's Claude profile verdict.
3. The arm-C freeze (founder decision; prepared in track E).
4. The native source (Q2) is registered, with its rights and yield, before any outcome is seen.
5. This packet is finalized: items 1–4 are filled from the records above with their hashes.
   Then comes the **owner's approval of source, route and quota**. The quota reading is taken at
   most 5 minutes before the cohort.
6. Only after that does SPEC-049/T014 run. Its deadline is 30 days after the new issuance.

## Questions for the owner at finalization (drafted, not asked yet)

- **Q1 Route:** "Subscription only, Haiku, EUR 0, with the D2 caps above." Confirm, or change
  through a new D2 decision.
- **Q2 Native source:** which tasks may the native cohort use? Each option needs rights stated:
  - (a) the frozen synthetic/constructed roster replayed natively. The result is descriptive
    only, per D3.
  - (b) new disjoint lineages built from this repository's history, with the owner granting
    rights.
  - (c) record infeasibility, so that T014 reports a feasibility result.
- **Q3 Infeasibility:** if gate 2 or gate 4 fails before the deadline, close T004 as
  "infeasible on the predetermined path". D7 then closes the harness as experimental.

## Infeasibility path

If any item cannot be met, the finalized packet records:
- which item failed, with its record;
- that no native capture happened.

T014 then keeps its native branch pending, as `tasks.md` requires. No item may be filled
from a double, a fixture or an estimate.
