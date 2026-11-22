# SPEC-078 evaluation protocol: owner review (T003)

The owner reviewed the draft protocol and decided each open item before the
freeze at `8ee703db` (2026-11-20 and 2026-11-21, recorded by the integrator;
not independently authenticated):

- OD-1: a prompt passes with at least 2 of 3 valid repetitions; Wilson 95 %
  lower bound at least 0.80; no 0/3 prompt after review; every class with at
  least half its prompts passing (the per-class clause was added by the owner).
- OD-2: splits of 24 feedback, 40 validation and 100 test prompts.
- OD-3: host Claude Code, model `claude-sonnet-5-5`.
- Coverage sentence of the analyze skill: corrected before the freeze (#1461).
- Gate 2 caps (OD-4): at most 4 rounds and 400 characters changed per edit.

Amendment 1 (2026-11-21, option 4) replaced Gate 2 with a hand fix measured on
a fresh split; its protocol is `evaluation-protocol-v3.md`.

## Deviations from the preregistered plan

1. **v3 independence.** Before the v3 split was built, BL.2b read three
   v2-test prompts (V2T-005, V2T-012, V2T-091) and their redacted traces in
   the Gate 1 zero-prompt review. The v3 templates are new wording, not
   derived from them, but v3's independence from v2 rests on the mechanical
   checks of `scripts/spec078_build_v3.py` (no shared fact pattern, no shared
   8-word window with v2, SPEC-069 or the skill), not on the author not having
   seen v2.
2. **Gate 2 not run.** The preregistered bounded-edit arm (T008) and its final
   evaluation (T009) were cancelled by the owner (Amendment 1, option 4) before
   any Gate 2 rollout. H-G2 was not tested; the hand fix measured on v3 is not
   H-G2 evidence.
