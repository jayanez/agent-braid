# SPEC-072: Requirements quality checklist

A requirements-quality checklist, not a proof or approval.

- [ ] Every requirement is testable by a named procedure.
- [ ] Every REQ has at least one scenario in `assurance.json`.
- [ ] H1, arms, budgets, stopping rules and analysis are fixed before held-out runs.
- [ ] The decision rule for H1 is unambiguous and uses D4 only.
- [ ] A null or negative result is stated as completing the protocol.
- [ ] The optimizer input path cannot reach held-out data.
- [ ] Contamination is checked before every optimizer call.
- [ ] GEPA is implemented from the paper with no vendored code.
- [ ] APO port and template conversion record upstream paths and hashes.
- [ ] No requirement promotes or writes the shipped skill.
- [ ] Open decisions OD-1 and OD-2 name their blocking tasks.
- [ ] Claims stay within observed hosts, models and prompt sets.
