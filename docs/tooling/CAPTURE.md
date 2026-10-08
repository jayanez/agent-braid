<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Capture admission preparation

`agent_braid.tooling_capture.prepare_attempt` prepares one private, hash-bound
admission receipt for a future SPEC-044 host/session adapter. It does not launch
Codex, Claude Code, MCP, a provider, or a fixture; issue or inspect a grant; or
append an `attempted` ledger event. An `admitted-not-started` receipt is only a
preflight record, never evidence that a session ran.

## Admission boundary

The caller supplies the approved registration, the exact clean candidate
checkout, the built candidate artifact, a validated 108-slot ledger, a selected
slot, authorization context, measured cumulative costs, stop observations, an
explicit receipt directory returned by `receipt_directory_for`, and a trusted
verifier. The module:

- validates the registration with the hash of the candidate artifact and reads
  the 18 fixture definitions and six prompts from that candidate's pinned
  `examples/tooling` inventory;
- checks the checkout commit and clean state against the registered commit,
  validates the ledger and refuses a slot with prior events or an existing
  admission receipt;
- binds the slot's exact host, model, SDK, OS, arm, fixture, prompt, candidate,
  registration, authorization references, cost-source references and stop
  state into a canonical SHA-256 receipt;
- requires measured cumulative costs for every declared field, compares them
  with prior ledger costs and registered caps, and stops when the trusted stop
  state reports an incident, an unrecoverable run, or two consecutive
  infrastructure failures; and
- asks the injected verifier to attest to the exact receipt subject before
  writing an exclusive mode-0600 file under a user-owned mode-0700 directory.

The receipt directory is fixed under the OS account home and keyed by the
canonical approved-registration digest. `receipt_directory_for(digest)` returns
this path; caller-selected aliases and alternate directories refuse. This
cohort-stable store is outside the candidate, registration and artifact paths.
A slot receipt is exclusive: a second or concurrent admission refuses and does
not overwrite it. Drift, a used slot, an open prior attempt, missing cost data,
unknown stop state, or a failed verifier requires preserving the slot and
reviewing the cohort; it does not create a retry. Candidate or input drift
requires a separately reviewed registration and new cohort.

## Trusted caller and authority references

The evaluator validates record shape and hashes. It cannot authenticate source
rights, provider consent, owner approval, identities, session observations or
cost measurements. The supplied `AdmissionVerifier` is therefore a trusted
caller boundary: a production implementation must authenticate the original
owner/source-right/provider decisions and the independent cost/stop sources,
then attest to the exact `subject_sha256`. This package provides no production
verifier. A test fake is only a deterministic unit control and cannot authorize
an actual attempt. A caller must not treat a structurally valid registration or
a locally constructible attestation as approval.

`AuthorizationContext` carries only references and hashes for context that
already exists. The registered `refuse-missing-grant` journey requires an
explicit no-grant context. The granted-execution journey requires a verifier-
checked existing execute grant and its exact plan digest. Recovery requires a
verifier-checked interrupted-run receipt, matching plan digest and existing
resume or abort grant. The admission layer has no grant issuance API, and
references are not grants. Capture begins only in a future separately reviewed
runner after it rechecks the receipt and obtains the required external decision.

`MeasuredCosts` is a reconciled cumulative observation including setup and all
prior attempts. Every field must be measured; unavailable is not zero. EUR,
tokens, input/output/retry tokens and wall time are checked as totals, while RSS
and disk values are treated as observed high-water values. The trusted verifier
must validate provenance and prevent undercounting; the module also rejects a
snapshot below any previously recorded ledger costs. `StopState` likewise must
come from an authenticated source, not a caller-entered green light.

## Current limits and required decisions

The current [`registration-draft.json`](../../examples/tooling/registration-draft.json)
is deliberately not admissible: it has draft/pending approval and source-rights
records, provider opt-in is false, exact rates and reviewers are unset, and the
rubric is not frozen. The proposed caps—€25, 4 million tokens, 8 hours, 4 GiB
RSS and 5 GiB disk—are proposals, not approved spending authority. No two
independent human reviewer identities or provider decision are recorded here.
Do not alter the draft into an approved registration to exercise this code.

This module is an admission and receipt-preparation slice for W15/W18/W19. It is
not a host/session capture runner, instrumentation source, stop controller,
actual receipt, or approval. No provider, host session, or grant was used by its
tests. Actual Codex and Claude discovery, skill loading, session events, complete
cost collectors, registered source rights and budgets, human scoring, and the
founder decision remain separate requirements in the
[evaluation protocol](../../specs/044-ai-tooling-evaluation/evaluation-protocol.md).
