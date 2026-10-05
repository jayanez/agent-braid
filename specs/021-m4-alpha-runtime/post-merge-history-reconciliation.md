# Post-merge evidence history reconciliation

PR #201 targeted base `cbe1580ca48d036e386531d843664e4795e64918` and was squash-merged from reviewed source head `54aa4bdf367dc5904dd31716762d01d94ecf4172` as `e9ae6645070b394ece67a36e5d082c874a0634e5`, after `develop` had advanced to `7227e2e69b4ea7c634fa5d68adbad8ff6dc6615e`. The squash integrated the PR changes on the updated base but did not retain the source branch's candidate commits as ancestors of `develop`.

Post-merge run `37325656702` failed both `scripts/validate_spec_kit.py` and the complete test suite because historical SPEC-011 evidence referenced `research/adoption/ADOPTION_PATHLINE.md`, which is not bound by the public export manifest. The record's evidence snapshot commit `b628ad065acf0b79b7e744a596ea898e7e4d89d1` was an ancestor of the reviewed PR head but not of the squash commit. SPEC-021's implementation, measurement, host and T013 review candidates are also ancestors of `54aa4bd`.

The corrective branch contains a no-tree-change `ours` merge whose second parent is the already-integrated PR source head. That bridge merge commit's tree is identical to the current `develop` tree. This PR also adds this reconciliation note, so its merge adds one documentation file. Merge it with a merge commit to make the exact candidate-bound history reachable from `develop`; squash or rebase would discard the ancestry bridge. Verify that `b628ad0` is an ancestor of `develop` after merge. The bridge does not change runtime behavior, the G4 NO-GO, or M3/M3.5 gates.

The separate tracking audit in post-merge run `37325656747` proposed repository-wide issue creation, linking and state operations. The audit did not apply them. Remote tracking remains a separate decision and authorization boundary.
