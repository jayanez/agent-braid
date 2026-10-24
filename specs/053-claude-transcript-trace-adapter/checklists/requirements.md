# Requirements-quality checklist

- [x] Every requirement has a scenario, a planned verification procedure and a named test file or procedure.
- [x] REQ-003 to REQ-010 say they are blocked by G0; only REQ-001 and REQ-002 are actionable. Only draft design artifacts exist for the blocked requirements.
- [x] The research protocol states population, source permissions, sampling frame, eligibility, exclusions, observed outcome versus proxy predictions, held-out unit and negative or inconclusive reporting.
- [x] Thresholds (C1a and C1b at least 1 each with C1b attribution, C2 at least 0.3 and above the reference-failure prevalence and the naive path-overlap precision, C3 attribution coverage of changes at least 0.60 (`5*attributed >= 3*changed`; zero changed files leaves it unmet), C4 at most 1 flagged negative control), the decision rule with its order of evaluation (executable in the decision vectors file) and the kill outcome are fixed before any data and pinned by a checker and tests with mutation controls. Only C1b gates PR5 and PR6, and a pass means feasibility not refuted.
- [x] Additive dependency on SPEC-023 is declared without changing its acceptance; the core analysis module is untouched (Article 15).
- [x] Hypothesis H-CW1, heuristic, analogy and formal claims are separated; no speed, safety or commutation claim.
- [x] Obtained evidence is empty and human review is pending; no approval, signature or freeze is inferred.
- [x] EUR 0 additional spend and the G0 aggregate-only retention are stated in the spec and the draft decision record; the product mapper's label is `allowlisted-metadata-and-counts` and lists its retained non-aggregate items.
- [x] The gate v2 contracts are written against the committed SPEC-052 v1 schemas (`schemaVersion`, `analysis.interactions`, replaced `limits` and `unobserved`, unchanged agent bound), and the SC-010 and REQ-009 wording states the bounded reading and the interface.
- [ ] Founder signature of the source and budget decision.
- [ ] Founder freeze of the preregistration with the pre-freeze bindings filled.
- [x] Clarification of the open questions that were listed in the spec: settled in the spec Clarifications (C3 binding, redefined by revision 3 as attribution coverage; R1 meaning, AT-2026-006 location, bounds, SPEC-023 hook form via plan RS-1 to RS-3). What remains open is listed in the spec's "Evidence and unresolved questions" (founder confirmation of the review amendments at freezing, signature, transcript schema pin, SPEC-023 ADR question, host verification and the SPEC-052 path-token amendment).
- [ ] Founder confirmation of the review amendments to C1, C2 and the order of evaluation (at freezing).
- [ ] G0 run, recorded outcome, and independent review.
- [ ] Implementation and acceptance of REQ-003 to REQ-010 (blocked until G0 passes).

Checked entries record document properties only.
