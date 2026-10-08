# SPEC-038 review and evidence workflow

## Current status — 2026-10-09

The founder accepted bounded M4 alpha engineering and evaluation completion
with negative utility. The historical SPEC-021 G4 NO-GO remains unchanged, and
tracking reconciliation remains pending guarded apply. See the [decision](whole-m4-founder-decision-20261009.json),
[closure packet](whole-m4-closure-packet.md), and [SC-008 evidence](evidence/sc-008.json).

## Capture status — 2026-10-08

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
was retried or resumed. Historical SPEC-021 G4 NO-GO remains visible. At this
capture-status snapshot, the later founder decision had not yet been recorded.
Source-project code and tests were not executed under this protocol.

This workflow prepares the bounded evaluator. Do not capture a workload or run
source project code from this quickstart.

1. Confirm that the exact local decision receipt matches the frozen
   `source-rights-manifest.json` and `protocol-review-packet.md`. The nine written
   source-rights and protocol decisions are already obtained; routine preparation
   within that scope does not require repeating them. Existing SPEC-013 M2
   decisions are separate historical evidence.
2. Independently assess the exact candidate source frame and current SPEC-020
   eligibility. Preserve exclusions and stop infeasible if no exact eligible
   workload exists; do not substitute sources.
3. Implement and validate the approved bounded evaluator, preserving the frozen
   SPEC-021 comparison, schedule, accounting, budgets and stops. Keep engineering
   checks on owned synthetic repositories separate from actual-workload evidence.
4. Freeze the exact harness and stable manifest. Obtain independent review and
   distinct capture authorization before any C09 capture.
5. Preserve every outcome and prepare the bounded interpretation packet and
   independent evidence review. The founder's bounded whole-M4 decision is now
   recorded; SPEC-021 G4 NO-GO remains historical and unchanged. Complete
   tracking only through guarded reconciliation and verify its result.

Historical status: source-rights, exact protocol, stable-candidate review and
capture authorization applied to `b85f7e5`. The exact two-operation manifest
passed static admission and technical review, but both launches stopped before
dispatch and those attempts obtained no actual workload outcome. The separately
approved e66f9a1 capture later completed as summarized above. Any future repair
requires fresh candidate-bound owner decisions.

## Preparation-only command

After the bounded harness is validated and committed, use a clean candidate
checkout and an existing external output directory. Supply the local exact
source/protocol decision receipt explicitly:

```sh
.venv-speckit/bin/python scripts/prepare_m4_real_workload.py \
  --source-repository /absolute/path/to/source-clone \
  --approval-receipt /absolute/path/to/spec038-exact-source-protocol-decision-20261008.json \
  --destination-root /absolute/path/to/fresh-private-trials \
  --output /absolute/path/to/external/spec038-manifest.json
```

The intended destination namespace must be new and outside source/candidate
storage. Preparation checks exact source and current runtime admission and writes
a manifest/provenance receipt; it creates no grant or runtime result. The command
refuses `--run`, `--execute` and `--registered`. Keep the manifest and local
rights records for stable review. A separate exact capture authorization is
required before the library capture path may be used; this quickstart supplies
no capture invocation or approval record.
