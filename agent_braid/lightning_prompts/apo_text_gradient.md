<!-- SPDX-License-Identifier: MIT -->
<!-- Converted from microsoft/agent-lightning agentlightning/algorithm/apo/prompts/text_gradient_variant01.poml at
commit 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x), Copyright (c) Microsoft Corporation, MIT License
(LICENSES/Agent-Lightning-MIT.txt). Changes: POML to Markdown; rollout traces replaced by content-free reward
vectors (SPEC-072 P4: no transcripts before BL.4). -->
You optimize a prompt template.

## Original Prompt Template

{prompt_template}

## Experiments with Original Prompt Template

Each line is one rollout: case id, host, whether the first attempt passed the D4 rule, whether the request was
schema-valid, the scoring reasons and any refusal code. No transcripts are available.

{experiments}

## Your Task

Produce a brief critique listing specific causes for the error or ways to raise reward next time.
Return a bullet list with concrete, testable changes (format, constraints, ordering, definitions).
