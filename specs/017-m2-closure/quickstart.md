# M2 clean-room protocol

Run this only after the radar, governance and implementation tracks have been
integrated and the candidate committed and published on a stable PR branch.
Use an exact 40-character commit hash and its exact `refs/heads/...` name,
Python 3.12 or newer and a source repository with full reviewed history.
The runner reads the public candidate and `develop` refs and requires the
candidate to descend from that remote `develop` commit.
The runner creates its own clone and virtual environment and writes a JSON
record even when a checked command fails.

```sh
python3 scripts/run_m2_clean_room.py <candidate-commit> \
  --candidate-ref refs/heads/<published-candidate-branch> \
  --source . --python /path/to/python3.12-or-newer \
  --output specs/017-m2-closure/reproduction.json
python3 scripts/validate_m2_closure.py readiness
```

After the separate founder decisions and closure record exist, validate the
candidate-to-closure interval with `python3 scripts/validate_m2_closure.py
closure`. Passing readiness is an internal reproducibility result, not founder
approval or independent validation. If the candidate or any hashed input
changes, freeze again and repeat the reproduction; never edit a captured
result to make it fit a different commit.
