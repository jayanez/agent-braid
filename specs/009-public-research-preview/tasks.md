# Tasks

- [x] T001 (REQ-001/SC-026): add immutable milestone closure anchors and validate
  candidate-to-closure intervals independently of moving HEAD. Verify with
  `PublicationTests.test_closure_anchors_bound_interval_not_moving_head`.
- [x] T002 (REQ-002/SC-027): implement the deterministic clean exporter and
  `public-export-manifest 0.1.0` schema. Redact machine-local paths in the export,
  rebind dependent digests, disclose all transformations and verify determinism
  and unsafe-input rejection with the paired publication test.
- [x] T003 (REQ-003/SC-028): implement explicit portable validation, root-manifest
  protection and ancestry-limit reporting without weakening private checks.
- [x] T004 (REQ-004/SC-029): implement public reproduction/release records and
  negative checks for stale, dirty or overclaiming evidence.
- [x] T005 (REQ-005/SC-030): add English community/release scaffolding and a
  non-mutating remote-cutover readiness record; keep all remote mutations pending.
- [x] T006: update proposal/status documentation and preserve ADR 0010 as
  `Accepted`; its architecture remains separate from remote authorization.
- [x] T007: capture local evidence, run all validators and reproduce a clean
  candidate root; the Spec Kit historical freeze is bound to the reviewed
  candidate and its historical authority/evidence snapshots.
- [x] T008: obtain explicit founder acceptance of ADR 0010 and the bounded local
  publication review; do not infer remote authorization. Recorded in
  `founder-review.json`; remote authorization remains false.
- [ ] T009: after a separate explicit authorization, create and verify the clean
  public repository, branches, rules, tag and GitHub prerelease, then archive the
  private repository.
