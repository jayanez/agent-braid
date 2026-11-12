<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<!-- Reflective mutation prompt for SPEC-072 GEPA, written from the description in arXiv 2507.19457 (Agrawal et al.,
"GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning"); no GEPA or DSPy text is copied. -->
You improve the guidance an assistant follows when it drafts an `analyze-work` request.

## Current Guidance

{prompt_template}

## Feedback on a Minibatch of Development Prompts

Each line is one rollout with this guidance: case id, host, whether the first attempt passed the D4 rule, whether
the request was schema-valid, the scoring reasons and any refusal code. No transcripts are available.

{experiments}

## Your Task

Reflect on what the failures have in common and which lessons are general rather than specific to one prompt.
Then write a complete new version of the guidance that keeps what works and fixes what failed.

Return only the new guidance text, with no explanation, headers or introduction before or after it.
