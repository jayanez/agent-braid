# Quickstart

From a clean Python 3.12+ checkout with the pinned development dependencies:

```sh
python3 -m unittest tests.test_git_partial_order -v
python3 -m unittest tests.test_git_counterexamples -v
python3 scripts/validate_spec_kit.py
python3 scripts/validate_change.py --base develop --profile quick
python3 scripts/validate_change.py --base develop --profile pr
```

The selected-order experiment is private and cannot replace the exhaustive
`plan-git`/`verify-git` evidence. A passing check supports only the finite
fixtures actually exercised. Review, clean-room reproduction and external
validation remain separate gates.
