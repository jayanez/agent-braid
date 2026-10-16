# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic advisory policies, always separate from execution authority."""
from agent_braid.system_one import STRICT_POLICY, DecisionRequest


def outcome(request: DecisionRequest) -> tuple[str, list[str]]:
    """Strict defaults abstain; incomplete fixture batches never become answers."""
    if request.envelope["policyId"] == STRICT_POLICY:
        return "abstain", ["calibration-absent"]
    if any(question.id not in request.state["ruleAnswers"] for question in request.questions):
        return "abstain", ["fixture-mapping-missing"]
    return "answered", []
