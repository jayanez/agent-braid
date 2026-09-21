# M0.5 closure reproduction

Run candidate checks with Python 3.12 or newer:

```sh
python scripts/validate_m05_closure.py --candidate
python scripts/validate_research_radar.py --milestone M0.5
python scripts/market_sizing.py
python -m unittest discover -s tests -v
python -m research.lab.controls
python scripts/constitution_replica.py check
git diff --check
```

After a clean candidate is committed, capture the isolated reproduction with:

```sh
python scripts/run_m05_clean_room.py <candidate-commit> \
  --source . \
  --python .venv/bin/python \
  --output specs/008-m0.5-closure/reproduction.json
```

The reproduction is internal and founder-supervised. It does not count as
independent validation. The final closure validator additionally requires three
explicit founder decisions and does not change repository visibility.

If the research-preview proposal is later approved for publication, use the
clean-export path in `docs/releases/RESEARCH_PREVIEW_PROPOSAL.md`. Do not make
the private repository public or rewrite its history without a separate explicit
authorization.
