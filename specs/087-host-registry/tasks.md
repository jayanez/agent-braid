# SPEC-087: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`python3 scripts/validate_change.py --base develop --profile quick`. No task adds a
host, adds a capability, changes `integrations/agent-braid/hosts.json` or rewrites
stored data. This first PR is documentation only; the tasks from T002 on wait for
owner approval (T001).

## Phase P0 — review and baseline

- [ ] T001 (REQ-001 / SC-001): Owner review of spec and plan, including the capability names in the plan's membership table.
  Dependencies: none. Target files: none. Verification: procedure_001. Planned
  evidence: `evidence/t001-owner-review.md`; obtained: none.
- [ ] T002 (REQ-005 / SC-005 REQ-006 / SC-006 REQ-007 / SC-007): Record the differential baseline from `develop` at 2a524884.
  Write the AST scan `scripts/host_scan.py` (tuples, lists, sets and dictionaries with two
  or more host identifiers in `agent_braid/` and `scripts/`) and generate from it every
  capability's members and order, every surface's stored spelling, the SHA-256 of
  `hosts.json`, and the outputs of the fixture commands of each surface in the plan.
  Fail if the scan finds a collection that is neither a plan site nor an exception.
  Requires T001. Target files: `scripts/host_scan.py`, `specs/087-host-registry/evidence/`. Verification: procedure_005, procedure_006, procedure_007.
  Planned evidence: `evidence/t002-baseline.json`; obtained: none.

## Phase P1 — registry

- [ ] T003 (REQ-003 / SC-003 REQ-011 / SC-011 REQ-014 / SC-014): Implement `agent_braid/host_registry.py` and its unit tests.
  Closed identifiers, alias, surfaces, capabilities and the pure query functions of the
  plan; no file, network, environment or clock access; no qualification or
  authorization field. Requires T001 and T002. Target files:
  `agent_braid/host_registry.py`, `tests/test_host_registry.py`. Verification:
  procedure_003, procedure_011, procedure_014. Planned evidence: `evidence/t003.json`;
  obtained: none.
- [ ] T004 (REQ-004 / SC-004 REQ-005 / SC-005): Normalize aliases at every host input and route stored spellings through the registry.
  Inputs call `normalize` before use; outputs call `spelling`; existing refusal codes
  stay. Requires T003. Target files: the input and output paths of sites 2, 3, 7, 16, 25
  and 4 in the plan, including the `--host` options of `plugin_cli`, `tooling_cli` and
  `view_cli`. Verification: procedure_004, procedure_005. Planned evidence:
  `evidence/t004.json`; obtained: none.

## Phase P2 — replace the sites

- [ ] T005 (REQ-002 / SC-002 REQ-006 / SC-006 REQ-009 / SC-009): Replace the Lightning, tooling measurement, subscription and host-event sites with capability queries.
  Sites 7 to 20 of the plan; feature-owned tables stay and a key-set test pins
  each to its query. Requires T004. Target files: `agent_braid/tooling_hosts.py`,
  `agent_braid/tooling_host_events.py`, `agent_braid/lightning_config.py`,
  `agent_braid/lightning_runner.py`, `agent_braid/lightning_hosts.py`,
  `agent_braid/tooling_subscription.py`, `agent_braid/tooling_evaluation.py`,
  `agent_braid/tooling_human_audit.py`, `agent_braid/tooling_subscription_estimate.py`,
  `agent_braid/tooling_interface_observer.py`, `agent_braid/tooling_model_identity.py`,
  `agent_braid/tooling_incremental_usage.py`, `agent_braid/lightning_schema.py`,
  `agent_braid/lightning_export.py`, their tests. Verification: procedure_002,
  procedure_006, procedure_009. Planned evidence: `evidence/t005.json`; obtained: none.
- [ ] T006 (REQ-002 / SC-002 REQ-008 / SC-008 REQ-009 / SC-009 REQ-013 / SC-013 REQ-015 / SC-015): Replace the harness, viewer, plugin CLI, installer and packaging-script sites and add the `hosts.json` consistency test.
  Sites 1 to 6 and 21 to 26 of the plan. `hosts.json` is not edited; harness
  qualification rows and gates are not changed; viewer labels `braid` and `other` stay
  in the viewer. Requires T004. Target files: `agent_braid/plugin_cli.py`,
  `agent_braid/harness_hosts.py`, `agent_braid/harness_components.py`,
  `agent_braid/view_cli.py`, `agent_braid/view_loom.py`,
  `agent_braid/tooling_cli.py`, `agent_braid/harness_hooks.py`,
  `agent_braid/tooling_install.py`, `scripts/build_native_plugin.py`,
  `scripts/reproduce_native_plugin.py`, their tests. Verification: procedure_002,
  procedure_008, procedure_013, procedure_015. Planned evidence: `evidence/t006.json`;
  obtained: none.
- [ ] T007 (REQ-002 / SC-002 REQ-010 / SC-010): Add the guard test against loose host lists.
  Reuses `scripts/host_scan.py`; the exception list is the ten files of the plan, each
  with its reason; a fixture proves it reports a new loose list. Requires T005 and T006.
  Target files: `tests/test_host_registry_guard.py`. Verification: procedure_002,
  procedure_010. Planned evidence: `evidence/t007.json`; obtained: none.

## Phase P3 — extension path, closure checks, evidence

- [ ] T008 (REQ-017 / SC-017): Document how a host is added and prove it with a fake host.
  A copy of the registry gains a fake host. The guard and key-set tests then report
  the feature-owned tables that lack it, and no other table. Requires T007. Target files:
  `docs/tooling/HOSTS.md`, `tests/test_host_registry.py`. Verification: procedure_017.
  Planned evidence: `evidence/t008.json`; obtained: none.
- [ ] T009 (REQ-012 / SC-012 REQ-016 / SC-016): Check that no frozen data and no other specification changed.
  Requires T006. Target files: none. Verification: procedure_012, procedure_016.
  Planned evidence: `evidence/t009-diff-scope.json`; obtained: none.
- [ ] T010 (REQ-005 / SC-005 REQ-006 / SC-006 REQ-007 / SC-007 REQ-014 / SC-014): Re-run the differential record after the change and compare it with T002.
  Rerun `scripts/host_scan.py` for the same table, identical bytes and sets apart from
  argparse usage text, then the full existing suites and `quick`. A difference is
  reported, not tuned away. Requires T008 and T009. Target files:
  `specs/087-host-registry/evidence/`. Verification: procedure_005, procedure_006,
  procedure_007, procedure_014. Planned evidence: `evidence/t010-after.json`; obtained:
  none.
