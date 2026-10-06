<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Run an owned Git fixture

Build two independent file edits, verify their replay, and publish a checked
result into a private local repository. This tutorial uses only a new temporary
fixture. Run it from the Agent Braid checkout after the README installation,
with Python 3.12+ and Git on Linux or macOS. No model, service or development
dependency is needed.

## Create the fixture

The generator refuses a nonempty directory. It creates its own source repository
and writes immutable request IDs; it does not inspect your projects.

```bash
DEMO_DIR=$(mktemp -d)
.venv/bin/python - "$DEMO_DIR" <<'PY'
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve(strict=True)
if any(root.iterdir()):
    raise SystemExit("Use a new empty demo directory")
source = root / "source"
source.mkdir()
env = {key: value for key, value in os.environ.items()
       if not key.startswith(("GIT_", "SSH_"))}
env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0", "GIT_DEFAULT_HASH": "sha1",
            "GIT_AUTHOR_NAME": "Owned demo", "GIT_AUTHOR_EMAIL": "demo@example.invalid",
            "GIT_COMMITTER_NAME": "Owned demo", "GIT_COMMITTER_EMAIL": "demo@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00"})

def git(*args):
    return subprocess.check_output(
        ["git", "-C", str(source), "-c", "core.hooksPath=/dev/null",
         "-c", "commit.gpgSign=false", *args], env=env, text=True).strip()

git("init", "-q", "-b", "main", "--template=")
for name in ("a", "b"):
    (source / f"{name}.txt").write_text("base\n", encoding="utf-8")
git("add", ".")
git("commit", "-qm", "base")
base = git("rev-parse", "HEAD")
operations = []
for name in ("a", "b"):
    git("checkout", "-q", "-b", name, base)
    (source / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
    git("add", f"{name}.txt")
    git("commit", "-qm", name)
    operations.append({"instanceId": name, "attemptId": f"{name}-attempt",
                       "source": {"kind": "commit", "revision": git("rev-parse", "HEAD")},
                       "dependencies": [], "uncertainPaths": [],
                       "declaredWrites": [f"{name}.txt"]})
git("checkout", "-q", "main")
for name in ("a", "b"):
    (source / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
git("add", ".")
expected = git("write-tree")
for name in ("a", "b"):
    (source / f"{name}.txt").write_text("base\n", encoding="utf-8")
git("read-tree", base)
request = {"gitRuntimeRequestVersion": "0.1.0-alpha", "repository": str(source),
           "baseRevision": base, "operations": operations, "order": ["a", "b"],
           "expectedFinalTree": expected}
analysis = {"gitAnalysisRequestVersion": "0.1.0-alpha", "repository": str(source),
            "baseRevision": base,
            "operations": [{k: v for k, v in op.items() if k != "declaredWrites"}
                           for op in operations]}
for name, value in (("request", request), ("analysis", analysis)):
    (root / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
print(f"Fixture ready: {root}")
PY
```

## Prepare and verify

```bash
.venv/bin/python -m agent_braid plan-git "$DEMO_DIR/analysis.json" \
  --evidence-output "$DEMO_DIR/replay.json" > "$DEMO_DIR/advisory.json"
.venv/bin/python -m agent_braid verify-plan "$DEMO_DIR/advisory.json" \
  --evidence "$DEMO_DIR/replay.json" --repository "$DEMO_DIR/source"
.venv/bin/python -m agent_braid prepare-policy-run "$DEMO_DIR/request.json" \
  --run-directory "$DEMO_DIR/result" --evidence "$DEMO_DIR/replay.json" \
  --advisory-plan "$DEMO_DIR/advisory.json" --mode parallel > "$DEMO_DIR/policy.json"
.venv/bin/python -m agent_braid verify-policy-plan "$DEMO_DIR/policy.json"
cat "$DEMO_DIR/policy.json"
```

Replay verification reports `status: verified`. Policy verification returns the
reconstructed plan with `consumerVerification.status: verified`. Preparation
creates no persistent result and grants no execution authority. Inspect the
source IDs, declared paths, result destination, budgets and exact `planDigest`.

## Authorize this local result

Copy the inspected digest into `PLAN_DIGEST`. This explicit acknowledgement is
the operator step; a model/tool caller cannot issue the grant through MCP.

```bash
PLAN_DIGEST='<copy the exact inspected planDigest>'
.venv/bin/python -m agent_braid grant-policy-run "$DEMO_DIR/policy.json" \
  --grant-store "$DEMO_DIR/grants" --acknowledge "$PLAN_DIGEST" > "$DEMO_DIR/grant.json"
cat "$DEMO_DIR/grant.json"
GRANT_ID='<copy the locally issued grantId>'
.venv/bin/python -m agent_braid execute-policy-run "$DEMO_DIR/policy.json" \
  --grant-store "$DEMO_DIR/grants" --grant-id "$GRANT_ID"
.venv/bin/python -m agent_braid verify-git-run "$DEMO_DIR/request.json" \
  --run-directory "$DEMO_DIR/result"
```

Execution reports `runtime.phase: completed` and
`runtime.status: verified-completed`; final verification reports
`status: verified-completed`.
The result is stored under `$DEMO_DIR/result/result.git`, at `refs/heads/result`.
The source files and refs remain unchanged by preparation and execution. The
grant is consumed once and expires after 300 seconds by default; repeat execution
does not apply the patches again. A refused or expired grant is not a completed
run.

For interruption, new resume/abort grants and stdio MCP configuration, follow
the [alpha runtime quickstart](../../specs/021-m4-alpha-runtime/quickstart.md).
This fixture demonstrates bounded engineering behavior. It does not establish
general concurrency safety, a speedup, or whole-M4 acceptance.
