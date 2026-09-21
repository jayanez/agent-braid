# Git adapter quickstart

Create a request conforming to
`schemas/0.1.0-alpha/git-analysis-request.schema.json`, then run:

```sh
agent-braid analyze-git request.json --format text \
  --provenance-output git-provenance.json
```

Commit sources use `{"kind":"commit","revision":"<ref>"}`. Worktree sources
use `{"kind":"worktree","path":"<path>"}` and must belong to the declared
repository. List known generated, ambiguous or otherwise incomplete paths in
`uncertainPaths`; they force conservative unknown coverage.

The provenance-output path is mandatory. The command reads Git state, writes the
requested evidence artifact, and emits an analysis report. It never changes the
repository and never authorizes execution, concurrency or merge.
