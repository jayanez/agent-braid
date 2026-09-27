# SPEC-018 implementation plan

## Technical context and scope

Use a standard-library Python module separate from M2 Git replay. Add bounded,
versioned consultative CLI producer and verifier.

## Constitution check before research

Articles 2–4 require named state, order and equivalence. Articles 6, 13–14 and
20 require verification, evidence and no execution authorization. Articles 8,
10 and 17 require crossing convention and claim-level separation. Article 9
requires negative controls. No MUST conflict was identified.

## Research, assumptions and alternatives

See research.md. Stable base anchors and fresh IDs permit deterministic sibling
sorting. Raw-index edits, deletes and external effects remain outside the
domain. A negative result is a valid protocol outcome.

## Design and compatibility

data-model.md and docs/theory/STRUCTURED_EXCHANGE.md define validation, replay,
residual and observation. propose-exchange emits evidence; verify-exchange
regenerates it. M2 contracts are untouched. M3.5 is separately scoped.

## Validation strategy

SC-001..007 map to tests/test_structured_exchange.py, the exhaustive corpus
and a temporary Git serialization witness.
Tamper and unsupported controls are mandatory. Run quick/PR profiles, then
clean-room reproduction. Record output and hashes after execution. Finite
success is no general proof.

## Constitution check after design

The design retains pure changes, named observation, full traces and consultative
status. It has no scheduler or execution route. No MUST is weakened.

## Human review and unresolved decisions

ADR acceptance, scientific interpretation, candidate freeze and M3 exit
decision are pending. Review whether this bounded class meets roadmap intent.
