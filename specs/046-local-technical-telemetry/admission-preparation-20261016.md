<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Local admission preparation — 2026-10-16

**Later documentary incorporation:** [D17/D18/D10](owner-decisions-20261016.md) now record the owner's scoped decisions, including pilot **NO-GO** and deferred final acceptance. T017/T018/T010 remain open. The preparation observations below retain their original boundary; the implementation and metadata commit identities are unchanged.

The implementation candidate is
`4f0a6bf407797bc4b682e6c5726dcd7a4f61bc28`, tree
`573656e292cb54a2b996d3ad28347537e38080ed`, based on
`466ada29b48bb768f8493ecf36a9472894af8440`. Its 107 changed files remain
the source under review. This subsequent metadata package neither changes
that source nor transfers its validation to a different implementation.

## Local preparation completed

- The retained external admission packet's 34 sealed files, 107 source
  bindings and 15 verbatim references match the candidate. Its seal SHA256 is
  `d76f841c1f76e41518b2ba856e2e79d0787dff13823248afa311ad3b60d9ef27`.
  This checksum is an integrity observation, not a signature or approval.
- The canonical [assurance record](assurance.json) now persists the historical
  authority and evidence snapshots generated at the clean implementation
  commit. It is byte-identical to the retained external frozen copy
  (`e143fa284e9e698fc99bbda11b7f411501301732a030fb38f6bf71a6dfa759f5`).
  Only snapshot mode/commit bindings changed; draft/pending review remains.
- The recorded full local PR profile for the implementation commit passed
  1621 tests with 11 explicit skips. The earlier umask-077 failure and both
  environment controls remain in the external packet; no failed run is
  relabeled. Metadata packaging checks are separate from that source run.
- [README](../../README.md), [AI-tool installation](../../docs/tooling/INSTALL.md)
  and [telemetry](../../docs/tooling/TELEMETRY.md) retain their candidate bytes;
  all 100 relative file links resolve locally. Instructions and native behavior
  have not been exercised in an AI host by this review.

The earlier plan, task evidence and copied admission matrix describe their
original uncommitted observations. This dated addendum supplies the later
commit/freeze state without rewriting those observations. A later metadata
commit packages the record; both historical snapshots continue to name the
implementation commit above.

## Remaining decisions and observation boundaries

SPEC-046/T010, SPEC-044/T017 and SPEC-044/T018 remain open: independent review,
architectural adoption, observation-contract disposition and exact-candidate
admission require their own records. The evaluation source-route dependency
also remains unresolved; no draft PR source is imported or merged.

The 11 skipped controls comprise five Linux-only process controls, four tests
requiring an explicitly isolated socat binary, one retained private-console
control and one unavailable private-history control. These are unexecuted;
this packaging supplies no replacement platform, dependency or private input.

Historical SPEC-044/T004 remains closed only in its previously approved bounded
domain for `482fbcc96227769f08768e79bc4d7f47d3445c4e`. Its task, assurance and
evidence bytes are preserved. No reproduction is reopened or repeated.

Admission, native inventory/loading/use, registration, 108 attempts, CLI
baseline, 36 cases/72 ratings, complete costs, human/founder acceptance and
M4.5 closure remain pending. No additional agent, AI host, provider operation,
user installation, publication, remote tracking write, push or merge occurs.
