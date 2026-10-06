# Synthetic adoption evidence program

This stdlib-only SPEC-026 increment validates offline synthetic intake and emits
canonical JSON to stdout. It cannot admit real organizations or reviewers, run
replay command strings, contact participants, change a release record, publish,
or make an adoption, benefit or independent-validation claim.

```sh
python3 research/adoption/evidence-program/program.py \
  research/adoption/evidence-program/fixtures/register.json \
  research/adoption/evidence-program/fixtures/frozen.json \
  --candidate aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
python3 -m unittest discover -s tests -p 'test_adoption_evidence.py' -v
```

`program.py` is also loadable through `importlib.util.spec_from_file_location`.
`freeze(register)` validates and returns input/window/manifest/record digests;
retain that packet separately **before observation**. `report(register, frozen,
candidate)` compares against those retained bytes. A caller who replaces the
frozen packet also changes the declared experiment; hashes are integrity bindings,
not approval or authenticated signatures. No contract supports real intake yet.

The [v1 contract](contracts/contract-v1.md) defines the exact bounded interface.
The fixture frame independently expects two eligible organizations, two workload
families, five episodes with one excluded, completion 1/3 over three known
outcomes with one missing, and 45 observed seconds over three complete costs with
one missing. Partial cost phases remain visible; missing totals are never zero.
Episode copies under new row IDs or organization aliases reject against the same
canonical unit/condition/rubric/source/binding identity. Distinct observations need
distinct integration or exact recording bindings; changed outcomes do not create
a new identity. Judgment is a proxy, separate from completion/errors/timing. Failed, abandoned,
unknown and excluded episodes remain in the report. The manifest keeps separate
units and baselines; stars and market substitutes are rejected.

A replayable contribution uses only a closed, bounded integer literal-write
model comparing orders of the same writes. The fixture's orders `[2,1]` and
`[1,2]` end at 1 and 2. Replay command strings remain provenance metadata and
are never dispatched. The divergence establishes only this synthetic terminal
observation. Rights gaps reject, incomplete replay metadata stays pending,
duplicate divergence does not count twice, and inconsistent declared results
request changes. No arbitrary Git/project execution is performed.

Maintainer/founder dossiers remain internal. An identified, complete, external
**synthetic** dossier yields `synthetic-external-proposal`, retaining positive,
negative or inconclusive outcome. It supplies no actual external reviewer or
release validation. Stale candidates and frozen evidence drift request changes;
missing identity, affiliation, conflict declaration, environment or command
metadata cannot qualify. No status sets independent validation to completed.

Reports contain allowed identifiers, outcome enums, numeric observations and
hashes; raw author/reviewer/affiliation/conflict/command/boundary text and raw
manifest descriptions are omitted. CLI refusals have fixed sanitized messages.
This is an allowlisted metadata boundary, not arbitrary secret detection.

The separate [historical reconciliation](../../../specs/026-adoption-evidence-program/legacy-status-reconciliation.json)
pins the original SPEC-002/T006 and SPEC-009/T009 obligations and the dated
2026-09-25 audit. It preserves the original bytes and authorizations. It does
not recheck today's remote state or close tasks from observed public visibility.

## Prospective real pilot gate

Before any future real-source extension, freeze admitted rights/retention,
eligibility and expected yield, collection window, organization/workload holdout,
task rubric, baseline versus report allocation/order, reviewer/adjudication,
budgets and complete-outcome/missing-label policy. Preserve setup/run/review/debug
time, failures, abandonment, errors and unknown outcomes separately from
participant judgments. Real integration benefit, contribution rights and
qualifying external reproduction require their own evidence and review.

This implementation does not update canonical schemas, the historical strategy,
SPEC-011 adoption dispositions, release validation, tracking, or founder decisions.
