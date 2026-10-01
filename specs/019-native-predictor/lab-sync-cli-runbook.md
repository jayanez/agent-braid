# M3.5 private lab synchronization: CLI runbook

**Scope:** synchronize only reviewed engineering decision files from the private
Kinetiq and SmartNotes source repositories to their separate private Agent
Braid labs. This procedure does not open an authoring window, register a real
source, copy a session journal, approve SPEC-019 or authorize execution.

## Repositories and credential boundary

| Source (`SOURCE`) | Destination (`LAB`) | Snapshot refs |
| --- | --- | --- |
| `jayanez/kinetiq-core` | `jayanez/kinetiq-braid-lab` | `lab/main`, `lab/develop` |
| `jayanez/smart-notes` | `jayanez/smartnotes-braid-lab` | `lab/main`, `lab/develop` |

Run every command once per row with `SOURCE` and `LAB` set to the exact values
above. The authenticated operator needs administration access to the source
and write access to its lab. Use a **different** Ed25519 deploy key for each
source. Create it with `read_only=true` through GitHub's REST API, then upload
only its private half to `M35_SOURCE_DEPLOY_KEY` in the matching lab's Actions
secrets. A deploy key is scoped to one repository, has no expiry and cannot
call GitHub's API; record and later revoke its ID. The lab's own `GITHUB_TOKEN`
has `contents:write` in the lab only. No personal access token or source
credential is placed in a lab Git tree, artifact or log.
GitHub may delete a deploy key created through an OAuth app token if that
token is revoked. After changing the operator's GitHub CLI authentication,
check each recorded key ID with `gh api repos/$SOURCE/keys/KEY_ID`; reissue
the key and lab secret if it disappeared. A successful old run does not
prove that a later scheduled run will retain access.

For the first pass set `SOURCE=jayanez/kinetiq-core` and
`LAB=jayanez/kinetiq-braid-lab`; for the second set
`SOURCE=jayanez/smart-notes` and `LAB=jayanez/smartnotes-braid-lab`.

GitHub's [deploy-key API](https://docs.github.com/en/rest/deploy-keys/deploy-keys),
[key limitations](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
and [checkout SSH input](https://github.com/actions/checkout/blob/v6/README.md)
define these permissions. The earlier GitHub App proposal is superseded for
this two-source pilot by proposed ADR 0018's CLI-managed deploy-key decision.

## 1. Check the exact scope before creating a credential

From an authenticated terminal, check `gh auth status`. For each row, inspect
the two repositories with `gh api repos/$SOURCE` and `gh api repos/$LAB`:
both must be private, active and show the operator's expected permissions.
List existing deploy keys with `gh api repos/$SOURCE/keys` and lab secrets and
variables with `gh secret list -R "$LAB"` and `gh variable list -R "$LAB"`.
Do not replace an unrelated key or secret. Set the explicit job gate to off:

```sh
gh variable set M35_SYNC_ENABLED -b false -R "$LAB"
```

Confirm that the lab `main` branch contains the reviewed `allowlist.json`,
`scripts/m35_lab_export.py`, `scripts/m35_lab_publish.py` and the rendered
`.github/workflows/sync.yml`. The template in Agent Braid is
`templates/m35-lab/sync.yml`; replace only `__SOURCE_NAME__` with the row's
source repository name. The job uses two `actions/checkout` steps with
`ssh-key: ${{ secrets.M35_SOURCE_DEPLOY_KEY }}` and does not retain source
credentials. From the Agent Braid candidate checkout, publish only that
reviewed workflow change to the matching private lab control branch:

```sh
BRAID_ROOT="$(pwd)"
LAB_DIR="$(mktemp -d "${TMPDIR:-/tmp}/m35-lab-control.XXXXXX")"
git clone "https://github.com/$LAB.git" "$LAB_DIR/repo"
sed "s/__SOURCE_NAME__/${SOURCE#jayanez\/}/g" \
  "$BRAID_ROOT/templates/m35-lab/sync.yml" \
  > "$LAB_DIR/repo/.github/workflows/sync.yml"
git -C "$LAB_DIR/repo" diff --check
git -C "$LAB_DIR/repo" diff -- .github/workflows/sync.yml
git -C "$LAB_DIR/repo" add .github/workflows/sync.yml
git -C "$LAB_DIR/repo" commit -m "Use read-only source deploy key for M3.5 sync"
git -C "$LAB_DIR/repo" push origin main
```

Check that this diff changes authentication only. Keep the private control
clone outside other repositories and remove it after verifying the push.

## 2. Create one read-only key and Actions secret

Use a fresh private temporary directory (`umask 077`) outside any Git
checkout. Never print the private key or pass it as a CLI argument. The public
key is safe to pass to the REST endpoint. Substitute a unique key title and
record the returned ID and SHA-256 fingerprint in a private operations
register, without the private key itself:

```sh
umask 077
KEY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/m35-deploy.XXXXXX")"
ssh-keygen -q -t ed25519 -N '' -f "$KEY_DIR/source" -C "m35-lab-readonly"
ssh-keygen -lf "$KEY_DIR/source.pub" -E sha256
gh api --method POST "repos/$SOURCE/keys" \
  -f title="m35-lab-readonly-20261001" \
  -f key="$(cat "$KEY_DIR/source.pub")" \
  -F read_only=true --jq '{id,title,read_only,enabled}'
gh secret set M35_SOURCE_DEPLOY_KEY -R "$LAB" < "$KEY_DIR/source"
gh secret list -R "$LAB"
```

Require `read_only: true`, `enabled: true` and a visible lab secret before
continuing. If secret upload fails, retain the private temporary key only
while retrying; if abandoning setup, delete the newly created remote key by
its exact ID. Once the lab secret is confirmed, remove the temporary key
files and directory. GitHub does not let you read a stored Actions secret
back; future recovery means rotating the key. Never reuse a deploy key across
the two source repositories. A REST 403 is an authorization failure: stop
instead of broadening token permissions without review.

## 3. Enable and exercise the exact reviewed workflow

After the updated workflow is on each lab's `main`, set the gate and manually
dispatch it once per lab:

```sh
gh variable set M35_SYNC_ENABLED -b true -R "$LAB"
gh workflow run sync.yml -R "$LAB" --ref main
gh run list -R "$LAB" --workflow sync.yml --limit 3
```

Inspect the new run with
`gh run view RUN_ID -R "$LAB" --json status,conclusion,jobs,url`;
inspect its job through the Actions REST API to
confirm a nonempty `runner_name` and executed steps. A queued or skipped job
is not a successful sync. Require the two source checkouts, two exact-file
exports and both filtered publications to succeed. Check the `lab/main` and
`lab/develop` refs, each `lab-snapshot.json`, the exact exported file list,
`allowlistSha256`, full `sourceSha`, and that the branch has no source Git
ancestry. Do not infer success solely from workflow dispatch returning a URL.

The schedule is `17 3 * * *` UTC. Treat delayed or missed scheduled runs as
gaps and use a manual dispatch when needed. A source blob SHA mismatch is an
intended failure: leave the lab snapshot unchanged, inspect the complete new
document under the source-owner/privacy rules, review a new allowlist pin in
the private lab and rerun. Never recalculate pins automatically to make a
failed sync pass. `M35_SYNC_ENABLED=false` stops both manual and scheduled
jobs without deleting evidence.

## 4. Observe and retire

Log each run ID, UTC time, conclusion, runner, source branch SHAs, snapshot
commit SHAs, pin mismatches and missed runs in the private operations
register. The lab branches contain only the reviewed files and snapshot
metadata; they are not a real-session feed. The separate audit workflow
still requires source permission, privacy review and a successful metadata
registration at least 24 hours before a fixed 14-day window. The diagnostic
audit run of 2026-10-01 used an intentionally incomplete payload: it proved
that a private runner started, but published no seal and registered no window.

At pilot retirement, set `M35_SYNC_ENABLED=false`, confirm no run is active,
delete the exact deploy-key ID from the source with `gh api --method DELETE
"repos/$SOURCE/keys/KEY_ID"`, and delete the lab secret with `gh secret
delete M35_SOURCE_DEPLOY_KEY -R "$LAB"`. Verify the key and secret are gone.
Rotate by creating a new key and lab secret, proving a successful sync, then
revoking the old ID. Review evidence retention before deleting any lab branch
or repository; branch deletion alone does not erase GitHub metadata or backups.

## Observed first run, 2026-10-01

After CLI setup, the Kinetiq lab run `36829164800` and SmartNotes lab run
`36829259038` both completed successfully with named GitHub-hosted runners.
Each run checked out source `main` and `develop`, exported exactly two pinned
Markdown files per branch, and published filtered `lab/main` and
`lab/develop` snapshots. The four snapshot trees, file SHA-256 values,
allowlist SHA-256 values and absence of source Git ancestry were checked
separately. The private operations register holds the exact key IDs,
fingerprints, source SHAs and lab commit SHAs. These runs prove the
synchronization path on those inputs only; they contain no local authoring
session, real eligible pair or audit registration.
