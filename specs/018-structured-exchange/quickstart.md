# SPEC-018 local reproduction

From a clean Python 3.12+ checkout:

```sh
python3 -m unittest tests.test_structured_exchange
python3 -m agent_braid propose-exchange specs/018-structured-exchange/fixtures/same-anchor.json --evidence-output /tmp/m3-exchange.json
python3 -m agent_braid verify-exchange /tmp/m3-exchange.json
python3 -m scripts.run_m3_experiment > /tmp/m3-finite-corpus.json
python3 -m scripts.run_m3_git_witness specs/018-structured-exchange/fixtures/same-anchor.json > /tmp/m3-git-witness.json
python3 scripts/validate_change.py --base develop --profile quick
python3 scripts/validate_change.py --base develop --profile pr
```

Expected finite result: zero false certificates in the declared corpus. A
passing check is neither independent validation nor founder approval.
