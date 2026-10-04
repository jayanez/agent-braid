# Proposal review and later validation

This feature is a draft. No new alpha command is implemented by these documents.
Use the existing isolated Python environment (>=3.12); install nothing globally.

Proposal checks from repository root:

```sh
.venv-speckit/bin/python -m scripts.validate_spec_kit
.venv-speckit/bin/python -m scripts.sync_github_tracking source
.venv-speckit/bin/python -m scripts.validate_change --base develop --profile pr
```

Expected: structural checks pass; human review remains pending and obtained
implementation evidence remains empty. Read spec.md, adr-0020-proposal.md and
closure-matrix.md together before scope acceptance. Do not run remote tracking
apply, launch hosts or invoke execution as part of proposal review.

After G0/G1, implementation defines executable tests and fresh reproduction
commands in each cut. Run quick after coherent increments, pr on a stable candidate,
then separate fresh reproductions and approved owned-fixture host exercises.
A real-host record must include exact versions/protocol/candidate and independent
consumer verification. Missing access or budget keeps that row pending.
Freeze a clean candidate before human review; record proposal adoption separately
from implementation acceptance and whole-M4 closure.
