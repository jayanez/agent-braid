# Offline foundations status

T001 adoption is recorded in [ADR 0027](../../docs/adr/0027-braid-harness-offline-foundations.md)
and [offline-adoption.json](offline-adoption.json). The reviewed kickoff packet
remains unchanged as the historical proposal; the later explicit decision adopts
only the offline T002–T004 foundations.

**T002–T004 are complete for this bounded offline profile.** T002 preceded T003
and T004, which were implemented in parallel with separate file ownership.

| Task | Obtained local engineering evidence |
|---|---|
| T001 | Explicit founder adoption, provenance inventory and fresh authority-impact review |
| T002 | Strict immutable manifest and independent identity verification; 11 focused tests |
| T003 | Bounded protected import, physical-ancestor isolation and conservative cleanup; 28 tests |
| T004 | Protected operator-file admission and single-use reservation; 20 tests |
| Composition | Three reserve-before-import, spent-on-failure and cleanup-authority controls |

All **62 focused tests passed without skips**, including real macOS case-alias
controls. **Stable PR validation passed all 14 commands and 2,173 tests with 24
skips for platform, tooling or private-fixture prerequisites**, zero errors/failures, and identical hashes for all 30 changed files before
and after execution. Independent Luna Latest review found no remaining blockers.
The implementation is uncommitted in the isolated `codex/har-kickoff-foundations`
checkout at baseline `a6329c828011d1468fed3dfa4e98f5a8531167e2`.

See [validation](evidence/offline-foundations-validation.json),
[review](evidence/offline-foundations-review.json),
[test log](evidence/offline-foundations-tests.log), and individual
[T002](evidence/t002.json), [T003](evidence/t003.json), [T004](evidence/t004.json)
records. The [internal contract](contracts/offline-foundations.md) specifies the
manifest bindings, root mapping and operator reservation boundary.

The intermediate quick profile is retained as nonpassing: its temporary copy
captured evidence/source drift during a correction, and its historical fixture
assumed the current 048 assurance remained historical. Stable hashes were rebound;
the fixture now restores exact tagged planning bytes in its disposable clone.
Both failures are resolved in the complete stable PR run. No validator or pin was
weakened. After PR, evidence-only packaging rechecks record/hash integrity.

The trusted operator composes reservation before import; failed import leaves
its reservation spent. There is no transaction coordinator, issuer or dispatch
interface in this slice. Guidance remains inert untrusted data. Read-only files
are not a sandbox against their owner; later consumers must independently verify.

Native/model/child/network/retry/cash limits remain zero for the admitted
laboratory, separately from developer/operator validation. No native/provider,
issuer/source/corpus, scientific/economic or full product acceptance is inferred.
The assurance remains draft with human review pending; no hosted CI, clean-room
or frozen implementation-commit reproduction is claimed.

T011 trusted context and T012 observation are the next independent prerequisites
for T005. They, T007 recovery, T009 full deterministic integration and native host
gates remain pending. This record starts no later task or promotion.
