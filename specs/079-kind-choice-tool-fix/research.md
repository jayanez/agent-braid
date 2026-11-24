# Research: SPEC-079

## R1 — Why tool-level, not skill text

Decision: change the tool. Evidence: SPEC-078 A0' on v3-test (PR #1490) after the T012 skill fix still
had 19/300 `units` attempts and two 0/3 prompts (V3T-002, V3T-027) reviewed as `model`; SPEC-069 T008
transcripts showed the same pattern. Alternatives: a third skill edit (rejected: two edits did not move
it); removing `units` (rejected: breaks SPEC-069 REQ-006 for legitimate declarations). Limit: the
mechanism (models ignoring `unknown`) is inferred from transcripts, not tested.

## R2 — Refuse vs hint (OD-A)

Decision: refuse with redirect. A refusal is a signal the host must act on in-turn; an `ok` report with
`unknown` was already ignored. Risk: a model that does not recover in-turn fails its first attempt;
measured, not assumed.

Disjoint means no dependency and no resource shared by two units with a write-like effect
(`analysis.WRITE_LIKE`): exactly the declarations whose pre-change report has only `unknown` pairs.
Sharing a `call` or an `emit`/`read` target is disjoint too. Limits recorded with the T001 review:
- Disjoint `units` declarations with partial coverage are refused as well. That follows OD-A, but v4
  holds no partial `units` case, so the cost of the second (`aim`) call for that host behaviour is
  not measured.
- The T001 change to `tests/test_spec069_units.py` and `scripts/spec069_generate_corpus.py` means their
  sha256 no longer match the values recorded in SPEC-069 `evidence/procedure_004`, `005`, `006` and
  `014`. Those closed records are not edited; they describe the pre-SPEC-079 files.

## R3 — Digest line

Decision: rewrite. "aim needs sha256:<64 hex> digests" reads as a precondition the host cannot meet
(no file to hash); transcripts showed hosts fleeing to `units` or `analyze`. The new text says any
well-formed label works. Limit: attribution of the 6 `analyze`-only failures to this line is a
hypothesis (H3).

## R4 — `analyze` tool

Decision: describe it, do not hide it. Hiding changes the tool list other hosts rely on; a description
is compatible.

## R5 — v4 split independence

Decision: new seed, new templates, mechanical leakage checks (inherited from v3 builder plus the new
descriptions). The author of the v4 templates does not open v2-test/v3-test prompt texts; independence
still rests on the mechanical checks. Data rights: synthetic, authored in-repo.

## R6 — Gate and power (OD-B)

OD-1 reused. At 100 prompts, >= 88 passing gives a Wilson 95 % lower bound >= 0.80. v3-test A0' scored
91/100 but failed on the 0/3 clause; the fix targets exactly that clause.
