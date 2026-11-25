# Feature specification

## Purpose and scope

State user need, exclusions and whether this is engineering or a research protocol.

## Authorities

Cite articles and documents; maintain their hashes in `assurance.json`.

## Requirements and acceptance scenarios

Use REQ-001 and SC-001 style stable IDs. State Given/When/Then observations and
failure cases. Map each requirement to scenarios, tests and planned evidence.
Give every MUST or MUST NOT obligation its own ID, including exclusions. Each
REQ needs scenarios in `assurance.json`.

## Non-functional requirements

Group operational and quality constraints here, each with its REQ ID:
observability, accessibility, availability, time and size limits. If none is
known, record an open question for the owner; do not invent one.

## Security and privacy

State each obligation about secrets, credentials or personal data as its own REQ
with MUST or MUST NOT. If none applies, write "No security or privacy obligation
applies:" followed by the reason.

## Terminology

Define the terms this feature introduces, one per line, and list the allowed
values of every enumeration. Shared terms follow `TERMINOLOGY.md`; link them, do
not redefine them. If none, write "No feature-specific terms."

## Scientific boundaries and compatibility

Record hypotheses separately, assumptions, domain, observation contract, execution
contract, limits, affected versions and compatibility. Do not require a hypothesis
to be true as a condition of completing a sound research protocol.

For an empirical protocol, define the target population, source permissions,
sampling frame, eligibility and exclusion reasons before collection. Distinguish
observed outcomes from human judgments or other proxy labels. State how label
coverage, disagreements and unresolved cases will be reported. If methods are
compared, name the held-out unit and prevent policy-dependent labeling or leakage.

## Risks and assumptions

One entry per line, each starting with "Risk:" or "Assumption:" and naming the
REQ it affects, or the task once tasks exist. If none is known, record an open
question for the owner.

## Exit criteria

State the evidence required to consider verification complete. If it is not
known, record an open question for the owner.

## Open questions

List each unresolved decision as a specific question with its owner, or write
"No unresolved questions."

## Evidence and unresolved findings

Keep planned and obtained evidence separate in the assurance record. Human review
and scientific interpretation remain explicit; a fingerprint is not approval.
Record feasibility failure, null and inconclusive outcomes as valid reports.
