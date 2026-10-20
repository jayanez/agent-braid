<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Local source and documentary reconciliation on rewritten develop

**Base:** rewritten develop `e474320eb763c33846665a0870677977b47d7a06` (`e474320e`).
**State:** local reconciliation prepared for a single local commit; no publication. No older commit object was
imported into this repository. The change files were reconstructed by comparing
the old base tree and the local source/documentary contents, then resolving each
file against the rewritten base.

## Preserved source and decision identities

The implementation snapshot remains C `4f0a6bf407797bc4b682e6c5726dcd7a4f61bc28`
(tree `573656e292cb54a2b996d3ad28347537e38080ed`), with metadata D
`b3809cbbaa0aa6ec1a1e50c6a841d840b753d94d` (tree
`a0fbf87cc1ba9cfafb31f054cbf39369f5b24fcc`) over historical base
`466ada29b48bb768f8493ecf36a9472894af8440`. The old feature commits are not
ancestors or objects in this checkout. All profiles, candidate manifests,
historical assurance snapshots, owner receipt, and raw evidence remain bound to
their original source and are copied byte-for-byte where included. The original
SPEC-046 assurance is archived at `historical/assurance-b3809cbbaa0a.json`; the
active `assurance.json` is a separate current draft, as explained below. The reconstructed
working tree is a new candidate with the local engineering validation recorded
in the linked report; independent review and admission remain pending.

D17 approves the additive observation contract while T017 stays open and T002
remains unchanged. D18 records coverage and pilot **NO-GO** while T018 stays open.
D10 acknowledges bounded engineering and defers acceptance while SPEC-046/T010
stays open. No native observations, registration, provider/host execution, extra
spend, independent review, architectural adoption or final acceptance is supplied.

## Conflict resolutions

- `README.md`: retains the rewritten develop overview and M4.5 context, adds the
  seven-spec source inventory and telemetry guide, identifies the reconstructed
  candidate with a separate local validation report, and preserves the historical
  evidence limits.
- `ROADMAP.md`: retains the remote milestone objective and accepted scope while
  updating the local source inventory and open native/review/acceptance gates.
- `docs/development/github-tracking.json`: retains all remote-source keys and
  milestone identities, adds SPEC-046 as locally open and updates the descriptive
  source counts. It performs no external tracking update.
- `docs/tooling/README.md`: retains rewritten-base assisted-evaluation guidance
  and adds current local telemetry status. Dated earlier snapshots remain clearly
  labeled historical.
- `specs/041-ai-tooling-skills/spec.md`: preserves the original skill contract
  and adds the boundary that skills do not enable telemetry; native loading/use
  remains pending.

The SPEC-044 task record carries forward the approved bounded T004 closure for
exact historical candidate `482fbcc96227769f08768e79bc4d7f47d3445c4e`. The block
is checked and unchanged from the approved local disposition; its original
failures, omissions, skipped checks and platform limits remain. No T004 procedure
was repeated. T002 is byte-identical. T017/T018 and SPEC-046/T010 remain unchecked.

## ADR identity collision

The rewritten repository assigns ADR 0023 to the second history correction. The
telemetry proposal formerly numbered 0023 in the frozen C/D documentation is
preserved byte-for-byte at `historical/adr-0023-local-technical-telemetry.md`
(SHA-256 `01552324429237a9f7114b223ee024687ba578d4efe72c8a0b6f49792125e989`).
Its current proposed record is `docs/adr/0024-local-technical-telemetry.md`.
This is a numbering correction only: the telemetry proposal remains proposed and
has not been adopted. The owner receipt, canonical decision JSON and historical
assurance pins were not rewritten to rename the decision after the fact.

The public `PR509_HISTORY_RECONCILIATION.md` and
`specs/046-local-technical-telemetry/pr509-dependency.json` retain their original
point-in-time observations. PR #509 is now integrated in rewritten develop; the
registration/interface/receipt modules are present with the previously recorded
hashes. Presence and hash equality do not provide authenticated process evidence,
registration approval, native observations or pilot admission.

Issue/tracking and milestone-description payloads remain local drafts bound to
their prior source observations. They are not ready for external application;
any later application needs a fresh source and digest audit. This tree records no
issue, project, pull request, publication or merge operation.

## Active draft validation after the history rewrite

The old active assurance named private C as both historical snapshots. C is not
in the rewritten ancestry or immutable export catalog, so portable validation
correctly rejected the first unbound reference, `data-contract.md`. Both the
history-equivalence assurance test and the Spec Kit baseline test reached this
same failure. This did not require changing a validator or an export manifest.

Following the documented Spec Kit draft-refresh workflow, the original assurance
(SHA-256 `e143fa284e9e698fc99bbda11b7f411501301732a030fb38f6bf71a6dfa759f5`)
is retained byte-for-byte at `historical/assurance-b3809cbbaa0a.json`. The active
record uses current authority and evidence modes, references proposed ADR 0024,
and remains `draft` with human review `pending`. Its obtained-evidence arrays
start empty: historical C/D results are preserved in the archive and evidence
files, and are not promoted to evidence of the reconstructed candidate. This
refresh does not revoke or extend D17/D18/D10 or change task completion.

Local validation outcomes and command logs are recorded in
[the reconciliation validation report](reconciliation-validation.md). A passing
profile establishes only its local engineering checks. Pilot NO-GO, open
T017/T018/T010, historical T004 limits and independent/human/founder gates remain.
The frozen export manifest, addenda, history-equivalence catalog and original
evidence files are unchanged. No old commit object or retained tag was imported.
