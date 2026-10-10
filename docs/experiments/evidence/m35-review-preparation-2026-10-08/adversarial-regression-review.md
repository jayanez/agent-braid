# M3.5 adversarial regression review follow-up — 2026-10-08

This follow-up was triggered by independent read-only adversarial review of the
source-free preparation candidate. Reviewers did not open source payloads,
change files, or post remote comments. The review was against the available
`develop` base `d5f379b`; the requested `e66f9a1` object was not present in the
review checkout.

## Findings and changes

The security review found that `capture_binding.py` used unbounded
`Path.read_bytes()` for supplemental files. The preparation checker now exposes
a fixed-allowlist reader that uses descriptor-relative, no-follow path opens,
rejects non-regular and multiply-linked files, and enforces the existing 1 MiB
bound. Binding reads only the returned bytes. Regressions cover disallowed
paths, symlink targets, FIFOs, oversized files, and hard links.

The protocol review found that the candidate inventory checker required exactly
five proposal rows, although source review may reject or merge candidates based
on evidence. The checker now accepts 0–100 proposals and rejects 101. The
documentation distinguishes proposal count from the unchanged minimum of five
eligible admitted experiment families. Candidate rejection/merge rationale
belongs in the separate human review record; the proposal inventory does not
claim or encode approval.

## Verification and limits

- `python3 -m unittest tests.test_m35_review_packet -v`: 13 tests passed.
- `capture_binding.py` reproduced a valid source-free packet commitment.
- `PATH="$PWD/.venv-speckit/bin:$PATH" python3 scripts/validate_change.py --base develop --profile quick`: selected executable validation passed. Its complete test suite ran 775 tests: 771 passed and four were skipped (three deferred real-predictor contract tests and one unavailable private historical commit check).
- A second read-only Luna Latest adversarial review found no remaining actionable bypass in the safe-reader changes. The inventory review confirmed the experiment's five-family eligibility gate was unchanged and identified the 0–100 bound and separate decision-record boundary; both are now explicit and tested.

These checks cover repository metadata and synthetic controls only. No
registration, source access, real-pair admission, annotation, fit, calibration,
holdout evaluation, scientific review, or founder decision occurred. The
previous preparation candidate is superseded. Human review must bind a newly
frozen candidate, and `pr` validation remains pending for that candidate.
