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

At this SPEC-020 integration snapshot, M4 remained open. Its tracking closure covered only the founder-approved first cut,
and neither this integration nor CI changes the M3/M3.5 empirical scenario gates,
independent external validation, production authority or broader runtime scope.

## Subsequent whole-M4 decision — 2026-10-09

The founder separately approved whole bounded M4 alpha engineering and evaluation
through item 22, with negative utility and the historical G4 NO-GO preserved.
See the [whole-M4 decision](../../specs/038-m4-real-workload-closure/whole-m4-founder-decision-20261009.json)
and [six-row closure packet](../../specs/038-m4-real-workload-closure/whole-m4-closure-packet.md).
The source records authority for bounded closure through governed reconciliation
after reviewed public delivery; current tracking is shown in the [M4 milestone](https://github.com/jayanez/agent-braid/milestone/6).
The historical SPEC-020 integration above does not provide the new approval. No source-promotion, arbitrary-code or real-external-effect capability
is adopted, and M3/M3.5 and independent scientific gates retain their own scope.
