# SPEC-019 proposed source-family review packet

**Status: proposal for human review only.** This metadata-only packet records
the current candidate workflow descriptions and requests decisions. It does not
identify eligible families, establish observed yield, authorize source access,
or approve data collection. No prospective session inventory, collection
window, or pair dataset has been admitted by this packet. It records no
content-review findings.

The Kinetiq evidence-pipeline shortlist and SmartNotes non-clinical
architecture/Spec Kit option list preserve the initial candidate boundaries
in the existing source register and pilot runbook. Three Agent Braid workflows
are proposed to explore whether separate natural engineering decisions could
form candidate families. Their natural occurrence, distinctness, independence,
rights and eligibility are unverified. A repository is not automatically a
distinct family, and the three Agent Braid candidates may be duplicates or
unusable. Do not manufacture tasks, changes, decisions, participant activity,
or quotas to retain a target number of rows or increase yield.

The exact machine-readable candidate inventory is
[`source-candidates.json`](source-candidates.json). Its current five records
mark distinctness, permission and eligibility review as pending. Reviewers may
reject or merge records based on evidence. Record each disposition and its
rationale in the separate
[`candidate-review-decisions.template.md`](candidate-review-decisions.template.md)
human review record; this inventory contains only current
proposals, not approval or rejection decisions. The checker accepts 0–100
proposal rows as a bounded metadata packet; candidate count is separate from
the experiment's minimum of five eligible admitted families. The entries are
not windows, registrations, admissions, or a sampling frame.

## Staged source review and authorization gates

Keep these stages separate for each proposed family. Until Stage 1 is recorded,
do not open file contents, journals, sessions or other source payloads.

1. **Metadata-only screening and permission to inspect.** Decide whether the
   described workflow naturally occurs and may be meaningfully distinct from
   every other retained family, including the other proposed Agent Braid
   workflows. Record the named source owner, potential participants and notice,
   source/data-rights basis, initial privacy decision, and permission for named
   reviewers to inspect exact pinned files. This stage may use workflow
   descriptions and repository path/blob metadata only; Git commits, timestamps
   and document diffs do not prove independent intent. Record immutable source
   revision and path/blob pins without reading blob contents. Stage 1 grants no
   export, collection, journal, registration or capture permission.
2. **Authorized content review.** Only after Stage 1 permission, named reviewers
   may open the exact pinned file contents within the approved local boundary.
   Review the complete text, confirm the exact content allowlist, excluded
   material, privacy and publication level, and record any revised permission
   decision before export or capture. Kinetiq's athlete/client and gait material
   and SmartNotes' patient, clinical, audio, transcript, review/audit and
   production material remain excluded. Agent Braid content and credentials
   need their own explicit boundaries. Content-review permission is not capture
   permission; any capture requires a subsequent, explicit source-specific
   approval.
3. Whether an authoring-boundary adapter can present one immutable base to
   each participant, capture independent proposal receipts before disclosure,
   and record cancellations, rejections, and all opened sessions. Define an
   independent completeness control for bypasses and reconcile every session
   against it. Sidecar hashes alone do not establish completeness or identity.
4. Whether the local private journal, custody controls, backup treatment and
   deletion process are acceptable. The proposed custody limit is deletion no
   later than 90 days after the documented post-window review, subject to a
   source-specific privacy decision and explicit backup-retention accounting.
   The journal, participant map, source content and per-item commitments stay
   outside Git and remote Actions artifacts.
5. Whether the current protocol is scientifically acceptable, including the
   two blinded reviewers and third-reviewer adjudication, unknown/disagreement
   handling, complete policy-blind annotation attempts, frozen family splits,
   and the requirement to preserve the deterministic verifier boundary.
   Review the unresolved P019-01 through P019-04 checklist items before labels
   or fitting.

## Future window and evidence gates

If and only if the relevant source-specific permission and protocol decisions
are recorded, a later proposal may specify one unaltered, fixed 14-day UTC
window per approved family, with exact start/end and event identifiers frozen
before collection. Each window requires its own successful metadata-only
remote registration at least 24 hours before its start, followed by the full
daily and final seal chain. A queued, skipped, billing-blocked, or runnerless
workflow is not a successful registration. Report missing runs and gaps as
such.

Before any label opening or training, enumerate all sessions and all
unordered candidate pairs, account for every exclusion with one primary
reason, reconcile the local ledger against the independent workflow
completeness control, and have a reviewer assess provenance and safe aggregate
publication. The current proposed workload protocol requires at least five
eligible families; a family-level train/calibration/three-holdout split; at
least 100 adjudicated known-label pairs overall; at least 20 useful and 20
not-useful known cases in untouched holdout; and both known classes in train
and calibration. These values are protocol candidates, not established power
or eligibility findings. If they cannot be met without extending a window,
changing population, cropping context, or manufacturing work, stop with an
inconclusive feasibility result and seek a separately reviewed decision.

The current founder decision approved bounded Kinetiq and SmartNotes
preparation, not per-source capture. It did not approve Agent Braid as a source,
open any real window, admit sessions or pairs, approve labels or training, or
accept the full protocol. Adding Agent Braid or any other source requires a
new explicit source/credential/service decision before access, key creation,
service setup, registration, or capture. This packet creates no credentials,
services, private lab, or source access.

## Current disposition

All current candidates remain proposals. Preserve actual zero observed pairs.
T001, T007 and P019-01 remain open; T002/T003 and human M3.5 review remain
gated. Nothing here closes SPEC-019, changes its assurance record, or implies
M4, System 1, or forecast-track acceptance.
