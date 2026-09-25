# External reproduction entrypoint

This is a practical starting point for independent reviewers. It is not an
independent review result or a request to report only positive outcomes.
Record the exact checkout, interpreter, Git version, commands, exit statuses,
environment limits and any negative or inconclusive observations.

1. Clone the public repository into a new directory and select the published
   `v0.1.0-alpha.1` tag to reproduce the preview's original bounded claims.
   Use Python 3.12 or newer in an isolated environment. Install only the
   development requirements needed by the selected validators.
2. Run `python scripts/validate_repository.py`,
   `python scripts/validate_contracts.py`,
   `python scripts/validate_publication.py --portable`,
   `python -m unittest discover -s tests -v`, and
   `python -m research.lab.controls`. These structural and finite checks do
   not prove scientific validity.
3. To inspect later M2 work, use a separate fresh clone of `develop`. The
   reviewed first-cut SPEC-012 candidate `7541ff437e2e2d6f558c5855ae76bb13067256cd`
   is not carried by the two permanent public branch tips. Before invoking
   `scripts/validate_spec_kit.py`, fetch that exact public Git object and keep
   it reachable in this disposable clone:

   ```sh
   git fetch origin 7541ff437e2e2d6f558c5855ae76bb13067256cd
   git update-ref refs/heads/validation/m2-source 7541ff437e2e2d6f558c5855ae76bb13067256cd
   python scripts/validate_spec_kit.py
   ```

   The local ref prevents the fetched object from becoming unreachable during
   the clean-public-root check. If the object cannot be fetched, record M2
   historical validation as unavailable; do not replace it with a passing
   current-tree test. Follow the [M2 quickstart](../../specs/012-m2-git-replay-planner/quickstart.md)
   for fixed-patch replay and the read-only T013 prototype.

Send the project a reproducible report with the candidate or tag identity,
environment, raw output, observation contract, tested scenarios and limits.
Negative and inconclusive findings are useful. Founder-supervised internal
reproduction remains separate from qualifying independent validation under
the [validation policy](VALIDATION_POLICY.md). This guide neither grants
execution authority nor changes `independent_validation: pending`.
