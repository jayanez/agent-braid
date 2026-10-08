# SPEC-019 preparation evidence, 2026-10-08

This increment delivers a metadata-only review packet and its read-only checker,
within T001/T007 preparation. It does not complete either task or the experiment.
No real payload was opened, no window registered, no pair admitted, no human
label collected, and no weight fit, calibration or holdout evaluation executed.
The real-data and scientific-review prerequisites remain pending.

`packet.json` binds six fixed review inputs and records five proposed workflow
descriptions only. `binding.json` binds those inputs, checker, tests and completion
plan with actual Python/platform provenance. `focused-tests.txt` records 29
passing synthetic/preparation controls. `technical-review.md` records the separate
Luna Latest medium review and its limits. Authority/evidence freeze identifies
the candidate separately; hashes and technical review do not authenticate source
permissions or replace founder/scientific review.

The milestone-9 tracking reconciliation closed only completed preparation tasks
T009 (#222) and T010 (#223). A follow-up audit reported `operations: []`; the
milestone remains open with seven issues. Existing T006/T008 history remains
unchanged. No new task or parent/milestone closure was inferred.

Corrected quick (escalated to sensitive) and stable PR profiles both exited 0.
Each full suite ran 772 tests, with 768 executed passes and four omissions: three
deferred real-predictor contract controls and one unavailable private historical
commit control. `validation-receipt.json` pins both completed outputs, commands
and results. These are software/structural checks, not clean-room experiment
reproduction or independent scientific validation. The original three deferred
predictor acceptance tests remain pending until gated implementation exists.

The initial full profile used Python 3.13 for its main process but an unactivated
PATH made three existing supervisor test workers use system Python 3.9. Those
workers failed to import the existing utility-budget observer, which requires a
supported Python. All three failures reproduced on unchanged `develop`; the
complete nine-test supervisor class passed when the isolated environment was
on PATH. Preserve the failed quick and interrupted PR runs separately; neither
is a passing profile. The corrected profiles explicitly prepend the isolated
environment to PATH. This was an invocation error, not a source change or proof
that any failed software check should be waived.

The first preparation clone subsequently contained three unreachable blobs after
intermediate index updates. Corrected profile attempts stopped at the existing
portable publication gate; their outputs remain separately recorded as failures.
Recovery used a new full public-develop clone with its own object store, restored
the exact reviewed SPEC-012 history, and transferred the final working-tree patch
only. No old `.git` was copied, object pruned, history rewritten, authority amended
or gate disabled. The older checkout remains intact. Final code is staged and
committed only once stable so superseded index-only blobs do not accumulate.

## Frozen preparation candidate

`candidate-receipt.json` identifies `47854298822dd6973e040947683bf72120395115` as the exact
authority/evidence candidate. The later commit packages this freeze only;
human review remains pending. The packet commitment is
`02457065ecd1a5f0a78a59a161e7dff8d4d83b6f22d2b5e45c5594326525477b`. No scientific
acceptance, source capture permission or model adoption follows from this record.

## Separate preparation reproduction

`preparation-reproduction.json` records the independent Luna Latest medium
reviewer replay in a new full clone and a new Python 3.13.11 environment. The
checker and input-binding commands matched the frozen candidate outputs byte
for byte; HEAD and Git status stayed unchanged. This reproduces the
preparation software only. No real experiment, scientific acceptance or human
approval is claimed, and the original frozen evidence snapshot remains bound
to the candidate above.
