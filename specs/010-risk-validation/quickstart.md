# Quickstart: validation profiles

Inspect the plan for all working-tree changes relative to `develop`:

```sh
python3 scripts/validate_change.py --base develop --profile quick --plan-only
```

Run fast invariant and affected-domain checks during development:

```sh
python3 scripts/validate_change.py --base develop --profile quick
```

Run the complete candidate gate once the implementation is stable:

```sh
python3 scripts/validate_change.py --base develop --profile pr
```

Use the sensitive profile when explicitly reviewing normative, scientific,
contract, supply-chain, validation-policy or generator changes:

```sh
python3 scripts/validate_change.py --base develop --profile sensitive
```

The plan reports deferred evidence boundaries. Run an applicable clean-room script
separately only for a frozen milestone, release, publication or scientific evidence
candidate. A successful profile does not constitute evidence capture, human review,
founder approval or independent validation.
