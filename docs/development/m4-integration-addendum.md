# SPEC-020 integration and tracking addendum

PR [#190](https://github.com/jayanez/agent-braid/pull/190) was merged by linear
integration into `develop` at `9b2c51580f681ad5f3531670e4bdd6825df685c4`.
Its tree matches the validated PR candidate
`13df5d5169f467c02f1877cbd49c17c91957141b` exactly. Original candidate objects
remain reachable through annotated review tags, including the canonical
`spec-020-reviewed-853df74` assurance anchor. Historical approvals were preserved.

The initial Linux CI failure was corrected by admitting Git's two read-only
fsck behaviors for a killed reference transaction. No runtime or schema code
changed after founder acceptance. PR CI [37157772299](https://github.com/jayanez/agent-braid/actions/runs/37157772299)
passed; post-merge CI [37158190795](https://github.com/jayanez/agent-braid/actions/runs/37158190795)
also passed. Tag-push checkouts separately failed the public unreachable-object
gate. Those failed executions are retained and are not reported as passing.

The reviewed tracking plan was
`61c6d2ac0991febd8191825952aba1753c0cc76787641ca761b4d56e9d5bedde`.
It created SPEC-020 [#191](https://github.com/jayanez/agent-braid/issues/191)
and its seven completed tasks (#192–#198), linked them and closed their bounded
tracking records. A subsequent repository audit returned `operations: []`.
The private Project's Specs and tasks, By milestone and By status views were
checked separately: SPEC-020 and all seven tasks are Done, assigned to M4.
The previously pending review decisions were not changed.

M4 remains open. Tracking closure covers only the founder-approved first cut,
and neither this integration nor CI changes the M3/M3.5 empirical scenario gates,
independent external validation, production authority or broader runtime scope.
