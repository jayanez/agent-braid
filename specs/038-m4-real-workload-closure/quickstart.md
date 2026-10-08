# SPEC-038 review and evidence workflow

## Development status — 2026-10-08

Exact source rights and protocol are approved. The bounded harness is merged and
validated; static admission and technical review cover two frozen operations and
20 treatment slots. See [implementation readiness](implementation-readiness.md)
for the evidence and scope. Earlier proposal descriptions retain their design-time
context. Owner stable-candidate/manifest review, capture and whole-M4 acceptance
remain pending.

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
5. Preserve every outcome. Prepare the bounded interpretation packet and
   independent evidence review. Whole-M4 status needs a new founder decision;
   SPEC-021 G4 NO-GO and M4-open remain historical facts until then.

Current status: source-rights and exact protocol approval obtained. The bounded
harness is merged; local quick/PR and hosted PR/post-merge validation have passed.
The exact two-operation manifest has passed static admission and technical review.
Owner stable-candidate/manifest review, separate capture authorization and
registered actual-workload outcomes remain pending.

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
