# Security Policy

## Current status

Agent Braid is in pre-implementation formalization. No production runtime or stable security boundary exists yet.

## Reporting a vulnerability

Do not disclose an exploitable vulnerability in a public issue. Use GitHub's private vulnerability reporting for this repository when enabled. If that channel is unavailable, contact the repository owner through a private channel listed on the owner's GitHub profile.

Do not include credentials, private repositories, proprietary code, personal data, or live exploit targets in a report.

## Security principles

- Unknown effects are not assumed safe.
- Destructive and externally visible operations require explicit policy.
- Declared tool metadata is evidence, not a trust boundary.
- Replay artifacts must avoid secrets and minimize sensitive state.
- Isolation strength is reported, not implied.
- Model output never grants authorization.
- Certificates must bind to versions and hashes to prevent evidence substitution.
- Adapters follow least privilege and restrict effect domains where possible.

## Anticipated threat model

The project expects to address:

- prompt or tool-description injection into effect analysis;
- false or incomplete effect declarations;
- time-of-check/time-of-use races;
- stale reads and lost updates;
- duplicated non-idempotent calls;
- unsafe replay of external effects;
- malicious or compromised agents;
- trace tampering and certificate confusion;
- secret leakage through logs, diffs, fixtures, or model context;
- sandbox and worktree escape;
- denial of service through schedule explosion.

Security claims will be versioned with the implementation and tested boundaries.
