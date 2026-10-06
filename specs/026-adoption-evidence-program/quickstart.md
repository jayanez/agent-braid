# Acceptance contracts and implementation quickstart

This document defines future tests. The evidence program, fixtures, validator
and `tests/test_adoption_evidence.py` are not implemented by this planning change.
The SC sections are draft assurance references and contain no passing evidence.

## Planning checks available now

```sh
SPECIFY_FEATURE_DIRECTORY="$PWD/specs/026-adoption-evidence-program" python3 .specify/scripts/python/check_prerequisites.py --json --require-spec --require-tasks --include-tasks
python3 scripts/validate_spec_kit.py
```

Expected: the spec package exists and structural validation passes on the complete
planning candidate. Structural success does not prove demand, utility, source
rights, reviewer independence or founder approval.

## SC-001 — Frame and permissions

Register synthetic organizations, alias duplicates, overlapping segment labels,
workload families and a prospective collection window. Submit a real-labelled
record with pending rights. Expected: canonical deduplication, distinct units,
visible eligibility/exclusion reasons and real record rejection without admission.
Save frame/window hashes, eligible counts and rejection outputs.

## SC-002 — Metric manifest

Use independently fixed counts, rates, costs and missing/excluded records.
Expected: exact formulas/units, denominator and evidence hash traceability, no
cross-unit sums, no stars/proxy substitution and no missing-as-zero behavior.
Save manifest, inputs, expected values and generated outputs.

## SC-003 — Usability and cost episode

Build synthetic baseline/report episodes with known completed/failed/abandoned
outcomes, distinct judgment labels, all four time components and an abstention.
Expected: observed versus proxy labels remain distinct, totals include all costs,
all episodes remain visible, and synthetic results never assert real utility.
For real collection first bind permissions/yield, rubric, allocation/order,
reviewer/adjudication and complete outcomes before comparing methods.

## SC-004 — Contribution and counterexample

Intake a replayable minimized synthetic divergence, duplicate contribution,
missing rights, unsupported workload and unreplayable case. Expected: admitted,
duplicate/rejected/pending dispositions with reasons and intact replay provenance;
negative results are preserved. Save inputs, replay output and review states.

## SC-005 — Externality and reproduction

Create maintainer rerun, anonymous claimed external, qualifying synthetic external,
stale candidate and missing environment/command/conflict dossiers. Expected:
maintainer remains internal; incomplete/externality claims stay pending; eligible
external evidence becomes a reviewed proposal with scoped outcome. No actual
release-validation status changes automatically. Save dossier validation results.

## SC-006 — Historical task reconciliation

Audit each original obligation in SPEC-002 T006 and SPEC-009 T009 against pinned
current evidence. Expected: one current reconciliation row per obligation with
observed state, authority, evidence and remaining decision; original frozen bytes
unchanged. A public repository alone cannot close prerelease/archive/review
obligations. Save hash bindings and proposed dispositions; no inferred approval.

## SC-007 — Audit, missingness and determinism

Alter a bound input hash, withdraw source permission, add contradictory/missing
records and vary a frozen window. Expected: affected metrics invalidated, all
reasons and denominators visible, privacy boundary retained. Identical admitted
synthetic inputs generate identical reports twice. Save both reports and controls.

## SC-008 — Milestone decision packet

Assemble register/manifest/pilot/intake/reproduction/reconciliation outputs.
Expected: observed/proxy/hypothesis and negative/inconclusive distinctions, links
to raw artifacts, independence/claim levels and pending founder decisions. No
outreach or publication side effect occurs and no popularity/proxy metric can
automatically approve a research claim. Save the current packet and decision log.

## Checks after implementation

After the planned test file and fixtures exist, run:

```sh
python3 -m unittest discover -s tests -p 'test_adoption_evidence.py'
python3 scripts/validate_change.py --base develop --profile quick
python3 scripts/validate_change.py --base develop --profile pr
```

Capture exact candidate/input/manifest hashes, environment, commands, results,
missing/excluded cases and limits. Run `pr` once on the stable candidate. Real
source admission, independent reproduction and founder/publication decisions
remain separate gates.
