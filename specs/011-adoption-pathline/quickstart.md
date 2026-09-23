# Adoption pathline quickstart

Run from the repository root in Python 3.12 or a compatible isolated environment:

```sh
python3 scripts/validate_adoption_tracks.py
python3 -m unittest tests.test_adoption_pathline -v
python3 scripts/validate_change.py --base develop --profile quick
```

The validator must report that the seeded records are structurally valid and that
none is adopted. The tests must reject missing hypotheses, invalid transitions,
missing source provenance and adopted tracks without a separate feature reference.

This command set validates governance structure only. It does not browse sources,
run provider SDKs, reproduce a paper, establish a market advantage or authorize
execution, merge or publication.
