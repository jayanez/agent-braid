# M1 internal closure

## Scope

Close M1 against a frozen candidate after measured Git baselines, explicit
condition-bound analysis, a founder-supervised clean-room reproduction and two
separate founder decisions. External validation remains visible and pending.

## Requirements and acceptance

- REQ-001: Measure file-overlap and Git merge baselines per scenario with
  decisions, duration, command count and Git exit status where applicable.
- REQ-002: Preserve `independent-candidate` for the version-bound scenario while
  explicitly recording mandatory version validation at the point of use.
- REQ-003: Reproduce both M1 corpora at an exact commit in a fresh clone and
  environment using Python 3.12 or newer, with input hashes, outputs, exit codes
  and clean initial and final repository state. The run MUST also check pinned
  Spec Kit rendering and the Codex-only, Claude-only and dual integration
  scenarios against temporary repositories that retain the candidate's complete
  Git history, and MUST require an approved M1 milestone-radar review. The
  sanitized environment applies to commit resolution, clone, checkout,
  virtual-environment creation and checks.
- REQ-004: Record separate founder scientific-review and milestone-closure
  decisions while preserving `independent_validation: pending` and the reviewer's
  conflict of interest.
- REQ-005: Preserve all existing analyzer, AIM, certificate, assurance and report
  contracts and make no execution, merge, safety, confluence or theorem claim.
- REQ-006: Reject closure when the candidate is outside the closure history,
  when any tree path other than an explicit post-freeze review record differs
  from the frozen candidate, or when the founder review omits mandatory evidence.

## Boundaries

This is internal founder-led closure, not external reproduction. Timings are
descriptive measurements on synthetic local corpora. Git mergeability and path
disjointness do not establish semantic independence or safe interleaving.
