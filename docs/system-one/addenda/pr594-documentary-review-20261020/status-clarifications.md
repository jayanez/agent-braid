# PR594 — status and chronology clarifications

Review target:06c3c6c6f15eb8a0b36fa4158ef7413a1b07b82d. These corrections apply to current navigation, not frozen source evidence.

| Review finding | Documentary correction | Preserved evidence |
|---|---|---|
| DOC-REV-001/P2: obsolete conditional T05 GO presented as current | Current index/resumption now lead with completed T05 engineering and final packet. The conditional-authority/start/finding/repair records are historical snapshots, with their pending states superseded only by later receipts. | Original conditional authority, all tests/failures and final packet remain unchanged. |
| DOC-REV-002/P2: T06 assignment pending without the later authorization boundary | The final T05 receipt predates the coordinator's new direct user authorization for Core API only. Current navigation records that later authorization, explicitly outside this PR and this conversation's implementation scope. | T05's original “new assignment required” was true at its receipt. It grants no T06 authority itself. |
| DOC-REV-003/P2: frozen DDP-T01 header still says coordinator review pending | Treat frozen design headers as the original pre-disposition candidate snapshot. The later coordinator final disposition verifies revision2 for bounded planning; use it for that review status. | Frozen five-file bytes and their actual validation/review chronology remain unchanged. No public schema adoption, full32-vector conformance or human/scientific acceptance is inferred. |

The current-read sources are the [T05 final packet](../t05-final-package-20261020/README.md) and [DDP-T01 final coordinator disposition](../verification-continuity-20261020/ddp-t01-final-disposition.json), with exact bindings in their adjacent records. The central index organizes older addenda as history instead of repeating incompatible “latest/current” labels.

The coordinator source thread01a14a9e-bea2-7c71-b818-c6d244a809cd, turn01a15889-7f54-70f2-becb-c4b044eb2251, was read during review. Its direct user instruction authorizes T06 Core API and adversarial EN/ES checks on M3 Pro with EUR0, human/training/activation pending, followed by an explicit documentary relay request. The coordinator reports Core API only, excluding MCP service/stdio; no completed T06 result is supplied by this documentary PR. This conversation's latest direct instruction is documentary review/preparation of PR594 without starting T06. The scopes are separate; no implementation source is touched here.

This clarification is an editorial status correction. It does not approve integration, create a code change, close scientific/human gates, refresh assurance snapshots or replace later review/CI at exact candidate bytes.

A subsequent [T06 proposed budget seam relay](t06-relay-scope.txt) was received while this review ran. It is recorded for handoff only, outside this PR's implementation or acceptance scope; source-bound T06 review remains the coordinator's responsibility.
