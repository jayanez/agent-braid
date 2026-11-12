<!-- SPDX-License-Identifier: MIT -->
<!-- Converted from microsoft/agent-lightning agentlightning/algorithm/apo/prompts/apply_edit_variant01.poml at
commit 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x), Copyright (c) Microsoft Corporation, MIT License
(LICENSES/Agent-Lightning-MIT.txt). Changes: POML to Markdown. -->
Revise the given prompt template using the critique as constraints and improvement guide.

## Revision Rules

1. Rewrite or restructure the prompt if critique implies it.
2. Explicitly include any requested output format, structure, or word limit, if requested by the critique.
3. Prioritize mechanism-first phrasing: define what to do, then how to do it.
4. Preserve placeholder variables inside curly brackets.

## Output Format

Return only the improved prompt template with placeholders intact. Do not include other explanations on how you
did it, or headers and introductory texts.

## Prompt Template

{prompt_template}

## Critique

{critique}
