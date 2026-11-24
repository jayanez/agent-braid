# SPEC-073 T010: owner rollback drill

<!-- Rendered by `python -m scripts.spec073_owner_promotion render-doc`; edit STEPS there. -->

This drill is procedure_009. You run every step; each human decision is an `--apply` with the
digest of the preview you just read. It promotes fixture candidate A, then B, rebuilds the
build check after each, and rolls back to A. Every write lands in one scratch work
directory: a temporary plugin home and a scratch copy of the mapped `SKILL.md`. The real
plugin home and the checkout's `SKILL.md` are never touched. The pairs are synthetic
(OD-4), so the evidence covers the mechanics, not a measured improvement. Revocation is not
part of T010.

Run the steps in one shell from the repository root:

```bash
PY=python3.13
D="$(mktemp -d)/spec073-drill"
```

## 1. Set up the fixture

Creates the work directory with a temporary plugin home, run `drill-1` holding candidates A and B, a scratch copy of the mapped `SKILL.md`, the synthetic pair files, and `drill.env`. It refuses a directory that exists or overlaps the real plugin home or the checkout.

```bash
$PY -m scripts.spec073_owner_promotion setup --workdir "$D" && . "$D/drill.env"
```

## 2. Preview promoting candidate A

Read the preview: `candidateSha256` is `$CAND_A`, `currentSha256` is null, `blockers` is empty and `requiredDecision` is `approved`. Nothing is written.

```bash
$PY -m agent_braid lightning promote --home "$D/home" --root "$D/root" --run-id drill-1 --candidate "$CAND_A" --registration "$D/registration-a.json" --evaluation "$D/evaluation-a.json" --identity "$D/identity.json" > "$D/preview-a.json" && cat "$D/preview-a.json"
```

## 3. Decide, begin and commit candidate A

Your human decision: apply with the digest of the preview you read. Expect `status` `committed` and `fileSha256After` equal to `$CAND_A`.

```bash
$PY -m agent_braid lightning promote --home "$D/home" --root "$D/root" --run-id drill-1 --candidate "$CAND_A" --registration "$D/registration-a.json" --evaluation "$D/evaluation-a.json" --identity "$D/identity.json" --apply --preview-digest "$($PY -m scripts.spec073_owner_promotion digest "$D/preview-a.json")" --actor owner --safety "$D/safety.json"
```

## 4. Rebuild check after A

Exports the drill registry into the scratch root and runs the release build check. Expect `release check passed`.

```bash
$PY -m scripts.spec073_owner_promotion check --workdir "$D"
```

## 5. Preview promoting candidate B

Expect `currentSha256` `$CAND_A`, `candidateSha256` `$CAND_B` and no blockers.

```bash
$PY -m agent_braid lightning promote --home "$D/home" --root "$D/root" --run-id drill-1 --candidate "$CAND_B" --registration "$D/registration-b.json" --evaluation "$D/evaluation-b.json" --identity "$D/identity.json" > "$D/preview-b.json" && cat "$D/preview-b.json"
```

## 6. Decide, begin and commit candidate B

Expect `status` `committed` and `fileSha256After` equal to `$CAND_B`.

```bash
$PY -m agent_braid lightning promote --home "$D/home" --root "$D/root" --run-id drill-1 --candidate "$CAND_B" --registration "$D/registration-b.json" --evaluation "$D/evaluation-b.json" --identity "$D/identity.json" --apply --preview-digest "$($PY -m scripts.spec073_owner_promotion digest "$D/preview-b.json")" --actor owner --safety "$D/safety.json"
```

## 7. Rebuild check after B

Expect `release check passed`.

```bash
$PY -m scripts.spec073_owner_promotion check --workdir "$D"
```

## 8. Preview the rollback

Expect `action` `rollback`, `currentSha256` `$CAND_B`, `candidateSha256` `$CAND_A`, `reason` `owner-rollback` and `requiredDecision` `human-apply`. Nothing is written.

```bash
$PY -m agent_braid lightning promote --home "$D/home" --root "$D/root" --run-id drill-1 --rollback > "$D/preview-rollback.json" && cat "$D/preview-rollback.json"
```

## 9. Apply the rollback

Your human decision: apply with the rollback preview's digest. Expect `status` `applied` and `activeSha256` equal to `$CAND_A`.

```bash
$PY -m agent_braid lightning promote --home "$D/home" --root "$D/root" --run-id drill-1 --rollback --apply --preview-digest "$($PY -m scripts.spec073_owner_promotion digest "$D/preview-rollback.json")"
```

## 10. Rebuild check after the rollback

Expect `release check passed`.

```bash
$PY -m scripts.spec073_owner_promotion check --workdir "$D"
```

## 11. Record the evidence

Writes `specs/073-lightning-promotion/evidence/procedure_009.json` with the journal, the committed decisions, the active and file digests and the check result. Expect `result OK`. Commit that file in the T010 evidence PR.

```bash
$PY -m scripts.spec073_owner_promotion evidence --workdir "$D"
```

## 12. Clean up

Removes the work directory (it refuses one that `setup` did not create).

```bash
$PY -m scripts.spec073_owner_promotion cleanup --workdir "$D"
```

Any refusal prints one line `lightning promote refused (<reason>)` and exits 2; stop and
report it. A test (`tests/test_spec073_owner_drill.py`) runs these exact commands on a
fixture, so this page stays in step with the code.
