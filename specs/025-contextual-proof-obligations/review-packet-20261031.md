# SPEC-025 source-bound proof review packet — 2026-10-31

Packet for the specific independent proof review of the anchored candidate.
**No reviewer is named, no review has been performed, and no theorem is accepted.**
Contacting external reviewers is not authorized by this packet.

## Owner decision (2026-10-31, recorded verbatim)

The repository owner (jayanez) decided on RES.1: «Cerrar con revisión pendiente» ("Close with review pending").
Effect: RES.1 closes with the specific independent proof review **pending**. That
review moves to a "Deferred" milestone; reopen criterion: a founder-named
independent proof reviewer. Tracking changes are applied by the coordinating
session after merge, not by this packet. The decision grants no proof acceptance
and no scientific or founder approval of the candidate.

## Frozen candidate

- Candidate commit: `6f4870ea8a885f3bf5c1e4e563a9a3759886d9aa` (public `develop`
  at capture; worktree clean before and after the checks).
- The checker, fixtures, mapping script, tests and anchored candidate are
  byte-identical to the previously reviewed candidate `a6329c828011d1468fed3dfa4e98f5a8531167e2`
  (`git diff` over the bound source paths is empty; recorded in the receipt).
- Obtained checks, exact argv, stdout/stderr and SHA-256 bindings of every packet
  file are in [the 2026-10-31 receipt](evidence/current-finite-receipt-20261031.json).
  The stable `pr` profile result (run on a fresh clone of the packet commit) is
  recorded only in the description of the pull request that adds this file. The
  checks above ran in a linked worktree, not a new clean clone; the clean-clone
  repetition remains the historical `evidence/internal-clean-clone.json`.

## Obtained finite results (candidate `6f4870ea`)

- 21 tests pass (20 contextual + the existing lone-surrogate Unicode regression).
- Two check/verify repetitions give byte-identical reports
  (`58b6862c…7f7f`, 14,914 bytes); manifest verdict stays `divergent`;
  `executionAuthorization` false, `proofAccepted` false.
- Independent anchored oracle: 32 orders, 86 involutive, 30 adjacent and 24 far
  checks, no mismatch; four excluded inputs refused (`a2b2820f…7e67`).
- Reproduction (Python 3.13 environment; exact argv in the receipt): `python3 -m unittest tests.test_contextual_lab tests.test_system_one_context.SystemOneContextTests.test_lone_surrogate_ids_and_values_refuse_domain_error`, then
  `python3 -m research.contextual_lab check|verify examples/contextual-lab/manifest.json`
  and `python3 scripts/crosscheck_contextual_proof_mapping.py --manifest examples/contextual-lab/anchored-manifest.json`
  with canonical (non-symlink) output paths such as `/private/tmp/...` on macOS.

## Packet contents for the reviewer

Review these exact bytes (hashes in the receipt `sourceBindings`):

1. `research/proofs/contextual-candidates/anchored-candidate.md` — candidate
   statements, obligations and excluded-model boundaries.
2. `specs/025-contextual-proof-obligations/premise-inventory.json`, `specs/025-contextual-proof-obligations/proof-tool-assessment.md` (no-tool/handwritten first).
3. `research/contextual_lab/checker.py`, `scripts/crosscheck_contextual_proof_mapping.py`,
   `examples/contextual-lab/*`, `agent_braid/structured_exchange.py`, `research/lab/model.py`.
4. Historical technical reviews (Luna) and receipts: `evidence/luna-*.json`,
   `evidence/packet-review-20261021.json`, `evidence/current-finite-receipt-20261021.json`,
   `evidence/internal-clean-clone.json`, `evidence/candidate-profiles.json`.

Open obligations the reviewer must address: closure for all finite abstract
carriers; bounded executable correspondence for insertion/sorting/hashes/residuals;
logical-result scope; exchange conventions and flattened observations; excluded
models (delete, nested, nondeterministic). LLM technical review and finite source
checks do not satisfy this gate.

## Historical status files

`assurance.json` and `evidence/technical-delivery.json` (bound in the receipt) keep
their "T007 pending" wording as of candidate `6f4870ea`; they are historical and
superseded for T007 by `tasks.md` and this packet.

## Decisions still pending (founder / human)

1. Name the independent proof reviewer (reopen criterion for the Deferred milestone).
2. Reviewer's findings and the accepted/rejected proof status of the anchored candidate.
3. Human scientific acceptance of the finite corpus and claims.
4. Any proof-tool adoption (ADR gate; not proposed here).
5. Any independent external reproduction (current runs share host, team and environment).

## Real-use evidence (2026-10-31)

No observations. Searched `~/.local/share/agent-braid/{evidence,coordination,identity,telemetry}`,
`~/.local/state/agent-braid` and `~/Library/Application Support/AgentBraid` for
SPEC-025/contextual-proof material: the only matches are unrelated SPEC-041 test
logs. The `agent-braid` CLI was not on PATH, so the telemetry database report,
`~/.claude/projects` (SPEC-053) and `~/.codex/sessions` were not queried. The proof
obligations are about abstract finite carriers; no real-use receipt informs them.

## Scientific limits

Finite evidence only; matching listed continuations is not universal equivalence.
Chronological traces stay distinct; unrepresented return values are not proved
preserved. No source expansion, provider execution or CoAgent comparator run.
