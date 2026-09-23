# Quickstart

Prepare a JSON request using the existing M1 Git request shape, with two to
four immutable commit sources descending from one base. Each operation has
`instanceId`, `attemptId`, `source`, `dependencies`, and `uncertainPaths`.

Generate evidence and a consultative plan:

```sh
agent-braid plan-git request.json --evidence-output replay-evidence.json
```

Independently replay and verify every recorded order against the local source
repository:

```sh
agent-braid verify-git replay-evidence.json --repository /path/to/repository
```

Use a preparation wave only as planning input for human review. Integration
remains serial, and both evidence and plan always carry
`executionAuthorization: false`. Stop at the emitted serial or manual-review
fallback if no verified candidate wave is produced.
