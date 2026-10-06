# Tasks

Draft contract/assessment work only. No new execution scope follows from this task list.

- [x] T001 (REQ-001/SC-001): Inventory existing private-runtime boundaries and write the capability refinement matrix.
  Dependencies: none. Targets: `refinement-matrix.md; current-runtime references`.
  Verification and planned evidence: Read-only source/contract audit; explicitly list unsupported isolation, observation and authorization premises.

- [x] T002 (REQ-002/SC-002): Draft promotion-specific scope, exclusive validation/CAS and recovery contract.
  Dependencies: T001. Targets: `promotion-contract.md; proposed-adr.md`.
  Verification and planned evidence: Specify grant/ref ownership/worktree restrictions and interruption outcomes; no source ref mutation or automatic ADR adoption.

- [x] T003 (REQ-001,REQ-002/SC-001,SC-002): Implement read-only promotion assessment and disposable negative-control dry-runs.
  Dependencies: T002. Targets: `scripts/check_runtime_refinement.py; tests/test_runtime_refinement.py`.
  Verification and planned evidence: Reject stale/dirty/attached/unknown targets and existing grants, bind source immutability and classify faults. Actual publication CAS remains a future feature.

- [x] T004 (REQ-003/SC-003): Assess installed isolation capabilities and propose bounded code-check probes.
  Dependencies: T001. Targets: `code-isolation-assessment.md; synthetic probe manifest`.
  Verification and planned evidence: Read-only inventory first; do not install or run project code. Obtain exact harmless-probe execution authority before probes; lack of enforcement is NO-GO.

- [x] T005 (REQ-004/SC-004): Specify external request/result/failure contracts and simulate retry/partial-effect controls.
  Dependencies: T001; SPEC-024 model or standalone abstract fixture. Targets: `external-effect-contract.md; tests/test_runtime_refinement.py`.
  Verification and planned evidence: No provider calls or credentials; retain ambiguous success, attempts/events and explicit non-inverse compensation.

- [x] T006 (REQ-005/SC-005): Capture feasibility evidence and prepare capability-specific ADR/GO-NO-GO packets.
  Dependencies: T003,T004,T005. Targets: `decision-packets.md; assurance.json; proposed-adr.md`.
  Verification and planned evidence: Run quick/PR and bind obtained outputs with limitations; refused/unknown capabilities have fallbacks and reconsideration triggers.

- [ ] T007 (REQ-005/SC-005): Record founder capability decisions and create separate implementation work only for adopted contracts.
  Dependencies: T006. Targets: `future decision records; ROADMAP.md; separate feature/contract versions`.
  Verification and planned evidence: Founder adoption is explicit. Preserve current M4 open/NO-GO and legacy grants. No new runtime capability is implemented by closing assessment tasks.

## Obtained technical evidence (2026-10-07)

The implementation and packet tasks above are complete within their explicit
synthetic/read-only domain. `evidence.json` binds focused controls, independent
Luna review and the stable 504-test PR profile (four documented skips). Human
acceptance, source rights, empirical interpretation, external reproduction and
publication/expanded-capability decisions remain separate. The checked packet
task records preparation and submission, not approval.
