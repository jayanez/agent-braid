# Bounded interaction laboratory

Experimental, standard-library-only Python 3.11+ models. No production runtime,
remote effects, LLM execution, retries, POR/DPOR or residual synthesis.
The [semantics](../../docs/theory/OPERATIONAL_SEMANTICS.md) and
[contracts](../../docs/architecture/DRAFT_0_2.md) define the interpretation.

From the repository root:

```bash
python3 -m research.lab explore examples/lab/independent.json
python3 -m research.lab verify examples/contracts/0.2.0-draft/exhaustive.json
python3 -m research.lab.controls
python3 -m unittest discover -s tests -v
python3 scripts/validate_contracts.py
```

The final command requires the pinned development dependency in
`requirements-dev.txt`; exploration, verification and controls do not.
CLI output is JSON on stdout. Verification exits nonzero for rejected or
unverified evidence. No files or external systems are mutated by these commands.

## Bounds and failure semantics

Fixtures contain 1–6 operations, 1–64 resources, expression depth at most 12,
and integer magnitudes at most `2**63 - 1`. Arithmetic overflow is an explicit
error. Versions use the same nonnegative bound. Names have at most 256 characters.
All model objects reject unknown fields. The CLI rejects inputs over 8 MB.

These bounds prevent this experimental enumerator from pretending to handle
unbounded state spaces. Guard failure, stale versions or unmet dependencies stop
an order as blocked; missing resources or arithmetic errors stop it as error.
Incomplete outcomes are inconclusive, even if their projections happen to match.

Certificates preserve the fixture operation order. The fixture digest binds all
inputs, including the observation. Exact observation retains chronological events;
independent writes can therefore differ under exact observation and agree under
a terminal projection. Neither result grants parallel execution permission.

The consumer recomputes outcomes without trusting the producer's verdict, but
both use the same reference interpreter. This is independent consumption, not an
independently implemented semantics or a machine-checked proof. Interpreter bugs
remain in the trusted base and require tests and subsequent formal work.

## Controls and evidence

The five negative controls reproduce lost updates, initial-context pair mistakes,
hidden-state observations, return-value dependence and write skew. The S3 control
checks 36 products and 216 braid triples for a known construction. These are finite
diagnostics, not tests of real tools or mechanized proofs of general theorems.

Executable files here explicitly use `AGPL-3.0-only`. This README and other
editorial research remain `CC-BY-SA-4.0` under the repository license map.
