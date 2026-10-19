# SPEC-041: Engineering quickstart

The experimental `agent-braid tooling` group and five product skills exist.
This procedure captures synthetic engineering controls, not host acceptance.
Use an isolated Python 3.12+ environment with the repository development
requirements. Keep its interpreter first on PATH for nested Python commands.

1. Read spec.md, plan.md, tasks.md, assurance.json and the SPEC-039 program.
2. Read [implementation status](implementation-status.md); refresh the two named
   conversations and only the relevant source/receipt deltas. Preserve the
   M4.5 frozen payload and existing approval boundaries.
3. Select the feature explicitly; run prerequisites:

```sh
SPECIFY_FEATURE_DIRECTORY=specs/041-ai-tooling-skills python3 .specify/scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
python3 -m scripts.validate_spec_kit
python3 scripts/sync_github_tracking.py source
```

4. Run the focused capture with a new absolute output path outside the checkout:

```sh
python3 -m scripts.run_m45_skills_acceptance --output-root /absolute/new/private/spec041-controls
```

The command runs fixed local tests in one supervised child, with a 300-second
work deadline, bounded retained streams and owned-group cleanup. It accepts no
host, provider, prompt, grant-store or arbitrary-command input. Failure, skips,
source drift, missing/duplicate tests or truncated output cannot pass. A failed
directory is retained; existing outputs are never overwritten or retried
automatically. Failures after reservation retain a terminal receipt while the
output filesystem remains writable; lost permissions/full disk are reported as
an output error and never a pass. `receipt.json` hashes the enumerated control
inputs and records test outcomes and limits; it does not hash the entire checkout.
`manifest.json` hashes retained files. `native-capture-plan.json` lists both
hosts' pending coverage without issuing permission or an attestation.

5. Run proportional quick validation after a coherent increment and the PR
   profile on the stable candidate. Installed-wheel verification remains a
   separate local procedure; synthetic capture does not imply package installation.
6. Obtain actual native receipts through the M4.5 continuation's registered
   SPEC-044/T002 route only after exact admission and approval. Complete original
   scenarios, freeze and request the applicable review/decision afterwards.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

## Current installation and telemetry

The original preparation steps above are historical planning context. For the implemented local candidate use [installation](../../docs/tooling/INSTALL.md), [telemetry consent and commands](../../docs/tooling/TELEMETRY.md) and [current alignment](../../docs/tooling/M45_ALIGNMENT.md). The five canonical skills neither select telemetry mode nor collect information. Their original native loading/use obligations remain pending; configuration consent and diagnostics belong to SPEC-042/046. No skill text or bundle is changed for telemetry.
