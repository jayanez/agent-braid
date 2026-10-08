# Source and protocol research record

## Development status — 2026-10-08

The exact successor candidate `e66f9a1b94fc5ebfbf784d9c48a76f53c1a656ee`
and manifest received independent review, owner stable-candidate approval
(item 18) and separate capture authorization (item 19). The single registered
capture completed all 20 treatments: 10 complete pairs, including four warm-up
and six measured pairs. All treatments were valid; the separate fresh-process
verifier inspected all 20 before conditional cleanup removed 40 run/grant paths.
The measured median serial/parallel total-wall ratio was `0.6538998702917553`,
favoring serial execution in this finite, uncontrolled sample.

See the [derived registered capture summary](evidence/registered-capture-summary-e66f9a1.json)
for exact bindings, complete denominators, costs, controls and unavailable
observations. The two historical `b85f7e5` pre-dispatch failures remain retained
in the [attempt summary](evidence/pre-dispatch-attempt-summary.json). No capture
was retried or resumed. Historical SPEC-021 G4 NO-GO remains visible and
whole-M4 founder acceptance remains pending. Source-project code and tests
were not executed under this protocol.

## Candidate source inspection

The only candidate considered here is the exact SPEC-013 public M2 corpus:

| Operation candidate | Public source | Base | Static patch inventory | M4 disposition |
|---|---|---|---|---|
| M2 observation normalizer | PR #137, `58351f812614058e53a8ee6aef1dd458f1bb70fc` | `f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6` | 3 modified paths; 64 changed lines; 7,872-byte diff | Historical design-time candidate; subsequently authorized and captured as summarized above |
| M2 counterexample reducer | PR #138, `083f1a390988a9527a5aaeb19133401243b1d714` | same | 5 paths (2 added, 3 modified); 999 changed lines; 55,208-byte diff | Historical design-time candidate; subsequently authorized and captured as summarized above |

These are authentic Agent Braid engineering changes and may have task relevance
to Git/runtime observation and reduction. They are not evidence of benefit for
the current runtime. The public full clone contains both commits and the stated
base; the base is an ancestor of each. Read-only `git diff --numstat` reports
only text counts; `git diff --summary` reports regular 100644 creations and no
mode changes. The operations touch disjoint paths, have no declared
dependencies, total 8 changed paths and 63,080 diff bytes. Their static A/M
text shape and counts fit existing 16-path/256-KiB limits. This supports a
statically eligible candidate source frame only. It does not prove runtime
preparation admission, expected tree verification, rights, protocol approval,
or capture authority. No runtime, source code, tests, hooks, network, or other
experiment was run. The 999-line patch is not by itself disqualifying.

## Rights and provenance

The M2 records provide immutable commit IDs, PR provenance, selected fixed
base, and fixed-path footprint descriptions. Both commit author/committer fields
name Juan Antonio Yáñez García (`jayanez@users.noreply.github.com`); parent
verified live PR metadata shows submitter `jayanez`, merged 2026-09-25, with
matching source head and base. This is provenance/authorship evidence only. The M2 founder decision accepted
only exact M2 inputs and states `executionAuthorization: false`; the M2 review
also says changed corpus/command/image/limits/observation needs separate review
and decision. These records do not identify a new M4 permission grant from
every source author/rightsholder, define M4 retention/reuse rights, or authorize
M4 collection/execution. The candidate commit author is the founder and PR submitter metadata is `jayanez`,
but that metadata alone did not confirm rightsholder capacity or exact M4
permission at design time. The subsequent owner decisions approve the rights
and protocol as described in implementation readiness. The frozen source-rights
manifest retains its original pending status; it is not the approval record.

## Protocol decisions proposed for review

1. One actual repository task family, exact commits and common base; no
synthetic substitute. Source rights and enough eligible operations are gates.
2. Compare actual SPEC-021 policy coordinator serial and parallel modes on
   identical inputs; do not compare ordinary replay with SPEC-020 alone.
3. Two operation orders (AB and BA), two unscored warm-up pairs per order, then
   three measured pairs per order (six measured pairs total). Freeze the exact
   seed, hashed pair order, balanced first-treatment schedule, and all ten pair
   slots in the stable manifest before results.
4. Fixed 45-minute total dispatch budget beginning before the first warm-up;
   360-second treatment observation deadline matching SPEC-021's pinned tool
   timeout. Stop new dispatch at 45 minutes, retain unexecuted slots, and let
   active work terminate only under existing cancellation/recovery behavior.
5. Each treatment total wall spans evidence/input through replay, preparation,
   grant, execution, consumer verification, report serialization, and cleanup,
   with explicit disjoint phase times and residual. A separate fresh Python
   process inspects all 20 treatment slots and verifies every completed result;
   report its time separately. Disclose rights, setup, operator, and observer
   costs and do not double-count nested phases.
6. Negative, inconclusive, and infeasible outcomes are valid; evidence of
   protocol compliance does not establish positive utility or milestone close.
7. Two explicit reviews: protocol/source-rights before implementation/capture;
   exact stable candidate/harness/manifest before a separate capture approval.

Current runtime admission passed without source/scope changes: two operations,
20 slots and equal predicted AB/BA trees. Historical candidate b85f7e5 later
received owner stable-candidate/manifest review and capture authorization, but
both launches failed before dispatch. Those attempts ran zero treatments. The
e66f9a1 successor subsequently obtained fresh exact owner decisions and completed
the capture summarized above; any future changed candidate requires new decisions.
The denominator/order/cost protocol and source rights are owner-approved; this
does not establish harness correctness or actual-task utility.
