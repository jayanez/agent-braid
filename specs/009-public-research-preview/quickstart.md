# Public research-preview validation

This protocol prepares and validates a clean export. It does not publish it.

```bash
python3 scripts/validate_repository.py
python3 scripts/validate_contracts.py
python3 scripts/validate_spec_kit.py
python3 scripts/validate_publication.py --source
python3 -m unittest discover -s tests -v
python3 -m research.lab.controls
git diff --check
```

Create two exports from the same exact candidate and compare them:

```bash
python3 scripts/create_public_export.py <commit> /tmp/agent-braid-export-a
python3 scripts/create_public_export.py <commit> /tmp/agent-braid-export-b
python3 scripts/validate_publication.py --export /tmp/agent-braid-export-a
python3 scripts/validate_publication.py --export /tmp/agent-braid-export-b
```

Expected: both payload inventories and manifests are identical apart from their
directory location. No `.git` directory, untracked source file or machine-local
absolute path is present. The transformation inventory identifies redacted records
and digest rebinding without exposing the removed paths. The validator reports
that private ancestry and original local-path-bearing bytes are unavailable in
portable mode and does not call the result independently validated.

Remote publication is a later founder-authorized operation. A blocked GitHub
Actions job is recorded as not executed.
