# M3.5 review correction candidate — 2026-10-08

This package records the follow-up to the earlier frozen preparation candidate.
The exact candidate source tree is commit `10944b5e8454602f7adc386f4b2eaff3ff628645`;
its source bytes are unchanged in the final frozen package; final review status
is pending until a human reviews that package.

`packet.json` reproduces the six-file metadata-only packet. `binding.json`
commits those files plus the checker, tests, completion plan, binding script and
adversarial review record. `focused-tests.txt` records the 13 source-free
adversarial regression tests. `validation-quick.json` records the successful
Python 3.13.11 `quick` profile, escalated to `sensitive`: 775 total tests, 771
passed and four skipped (three deferred real-predictor controls and one
unavailable private historical commit check).

The adversarial reviewers used Luna Latest (`gpt-6-luna`), medium effort. One
reported the unsafe supplemental file read and exact-five candidate roster;
independent follow-up reviews found no remaining actionable read-boundary
bypass and confirmed the experiment's five-eligible-family threshold is
unchanged. The review checkout lacked requested base `e66f9a1`, so review was
against available `develop` `d5f379b`. No source payload was opened.

The stable `pr` profile passed on code-identical commit `3e91789`; its complete
log is `validation-pr.txt`. Independent human review, source decisions and
experiment gates remain pending. This package records neither consent nor permission,
registration, source completeness, real admitted pairs, annotation, model fit,
calibration, holdout results, or founder approval.
