# Quickstart

From a clean Python 3.12+ checkout, run the focused counterexample tests:

```
python3 -m unittest tests.test_git_counterexamples -v
```

Then `python3 scripts/validate_spec_kit.py` and
`python3 scripts/validate_change.py --base develop --profile quick` (this
touches `agent_braid/`, so the planner escalates to its `sensitive` profile,
which needs `jsonschema` for the contract gate; run it in the pinned
`agent-braid-t013:py312-git247-v1` image if the host Python lacks it). Run
`--profile pr` once on a stable candidate.

The positive reduction cases use a controlled divergent replay backend.
Bounded local probes found no real all-complete divergent fixture, so the
focused tests do not establish one. Real Git tests cover input rejection and
timeouts.

Development validation does not capture a frozen feature evidence artifact or
complete human/founder review. Those boundary gates remain pending in
`assurance.json` (`human_review: "pending"`).
