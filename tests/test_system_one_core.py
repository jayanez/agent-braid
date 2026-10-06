# SPDX-License-Identifier: AGPL-3.0-only
"""Exact synthetic contract controls, without workload or scientific claims."""
from copy import deepcopy
import json
import unittest

from agent_braid.system_one import (BACKEND_ID, CAPABILITY_ID, CONTEXT_VERSION, DIAGNOSTIC_POLICY,
    MAX_BYTES, STRICT_POLICY, VERSION, InvalidDecision, build_answers, canonical,
    digest, evaluate, parse_json, validate_request, validate_response)


def fixture(*, request_id="r1", policy=DIAGNOSTIC_POLICY, choice="true") -> dict:
    state = {"sourceKind": "synthetic", "ruleAnswers": {"q": choice}}
    return {"contractVersion": VERSION, "requestId": request_id, "state": state,
            "stateDigest": digest(state), "questions": [{"id": "q", "type": "boolean", "instructions": "Synthetic only",
              "options": [{"id": "false", "description": "no"}, {"id": "true", "description": "yes"}]}],
            "capabilityId": CAPABILITY_ID, "contextVersion": CONTEXT_VERSION, "backendId": BACKEND_ID,
            "policyId": policy, "budgets": {"maxInputBytes": MAX_BYTES, "maxQuestions": 32,
              "maxOptions": 32, "maxTokens": MAX_BYTES, "deadlineMs": 5000}}


def encoded(value) -> bytes:
    return canonical(value)


def repair_state(value) -> None:
    value["stateDigest"] = digest(value["state"])


class SystemOneCoreTests(unittest.TestCase):
    def test_every_primitive_answer_and_immutable_data(self):
        value = fixture()
        for primitive, options, choice, expected in (
            ("boolean", [{"id": "false", "description": ""}, {"id": "true", "description": ""}], "false", None),
            ("choice", [{"id": "z", "description": ""}, {"id": "a", "description": ""}], "a", None),
            ("score", [{"id": "low", "description": "", "value": -2}, {"id": "high", "description": "", "value": 7}], "high", 7)):
            with self.subTest(primitive=primitive):
                value["questions"][0].update(type=primitive, options=options)
                value["state"]["ruleAnswers"]["q"] = choice
                repair_state(value)
                raw = encoded(value)
                request = validate_request(raw)
                with self.assertRaises(TypeError):
                    request.state["ruleAnswers"]["q"] = "forged"
                with self.assertRaises(TypeError):
                    request.envelope["questions"][0]["options"][0]["id"] = "forged"
                response = evaluate(raw)
                self.assertEqual(response["status"], "answered")
                answer = response["answers"][0]
                self.assertEqual(answer["choiceId"], choice)
                self.assertEqual(answer["expectedScore"], expected)
                self.assertEqual(answer["argmaxScore"], expected)
                self.assertEqual(answer["pTrue"], 0 if primitive == "boolean" else None)
                frozen = validate_response(response, request=request)
                response["answers"][0]["choiceId"] = "forged"
                self.assertEqual(frozen.to_dict()["answers"][0]["choiceId"], choice)

    def test_uniform_distribution_tie_entropy_and_expectation(self):
        value = fixture()
        value["questions"][0].update(type="score", options=[{"id": "z", "description": "", "value": 0}, {"id": "a", "description": "", "value": 10}])
        value["state"]["ruleAnswers"]["q"] = "z"
        repair_state(value)
        answer = build_answers(validate_request(encoded(value)), [[0.5, 0.5]])[0]
        self.assertEqual(answer["choiceId"], "a")
        self.assertEqual(answer["expectedScore"], 5)
        self.assertEqual(answer["argmaxScore"], 10)
        self.assertEqual(answer["rawTopProbability"], 0.5)
        self.assertAlmostEqual(answer["concentration"]["value"], 0)

    def test_parser_rejects_ambiguity_depth_and_nonfinite_before_backend(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}',
                    b'{"a":9223372036854775808}', b'{"a":' + b'9' * 100 + b'}',
                    b'{"a":"\\ud800"}', b'\xef\xbb\xbf{}', b'{} trailing', b'\xff',
                    b'{"a":' + b'[' * 16 + b'0' + b']' * 16 + b'}'):
            with self.subTest(raw=raw[:40]):
                self.assertEqual(evaluate(raw)["status"], "refused")
                with self.assertRaises(InvalidDecision):
                    parse_json(raw)
        # Brackets and escaped quotes inside strings do not count as nesting.
        self.assertEqual(parse_json(b'{"a":"[[[[[[[[[[[[[[[[[[\\\""}')["a"], '[' * 18 + '"')
        self.assertEqual(parse_json(b'{"a":' + b'[' * 15 + b'0' + b']' * 15 + b'}')["a"][0][0][0][0][0][0][0][0][0][0][0][0][0][0][0], 0)

    def test_raw_canonical_and_render_exact_boundaries(self):
        value = fixture()
        raw = encoded(value)
        self.assertEqual(evaluate(raw + b' ' * (MAX_BYTES - len(raw)))["status"], "answered")
        self.assertEqual(evaluate(raw + b' ' * (MAX_BYTES + 1 - len(raw)))["reasonCodes"], ["input-budget-exceeded"])
        value["budgets"]["maxTokens"] = 1
        self.assertEqual(evaluate(encoded(value))["reasonCodes"], ["render-budget-exceeded"])
        value = fixture()
        value["requestId"] = "é" * 32
        self.assertEqual(evaluate(encoded(value))["status"], "answered")
        value["requestId"] += "é"
        self.assertEqual(evaluate(encoded(value))["status"], "refused")

    def test_question_and_option_limits_and_exact_budget(self):
        value = fixture()
        value["questions"] = []
        value["state"]["ruleAnswers"] = {}
        for index in range(32):
            question = {"id": f"q{index}", "type": "choice", "instructions": "",
                        "options": [{"id": f"o{i}", "description": ""} for i in range(32)]}
            value["questions"].append(question)
            value["state"]["ruleAnswers"][question["id"]] = "o0"
        repair_state(value)
        self.assertEqual(evaluate(encoded(value))["status"], "answered")
        value["budgets"]["maxQuestions"] = 31
        self.assertEqual(evaluate(encoded(value))["status"], "refused")
        value["budgets"]["maxQuestions"] = 32
        value["budgets"]["maxOptions"] = 31
        self.assertEqual(evaluate(encoded(value))["status"], "refused")

    def test_malformed_domain_ids_numeric_and_unknown_fields(self):
        mutators = (lambda x: x.update(executionAuthorization=True),
                    lambda x: x["budgets"].update(deadlineMs=True),
                    lambda x: x["budgets"].update(deadlineMs=0),
                    lambda x: x["budgets"].update(maxTokens=1.0),
                    lambda x: x.update(backendId="provider"),
                    lambda x: x.update(stateDigest="a" * 64),
                    lambda x: x["questions"].append(deepcopy(x["questions"][0])),
                    lambda x: x["questions"][0]["options"].append(deepcopy(x["questions"][0]["options"][0])),
                    lambda x: x["questions"][0].update(instructions="é" * 2049),
                    lambda x: x["state"].update(sourceKind="real"),
                    lambda x: x["state"]["ruleAnswers"].update(unknown="true"),
                    lambda x: x["state"]["ruleAnswers"].update(q="unknown"))
        for mutate in mutators:
            value = fixture()
            mutate(value)
            response = evaluate(encoded(value))
            self.assertEqual(response["status"], "refused")
            self.assertIsNone(response["requestId"])
            self.assertFalse(response["executionAuthorization"])

    def test_score_invalid_types_order_and_empty_rubric(self):
        for scores in ([], [0], [0, 0], [2, 1], [False, 1], [0, 1000001]):
            value = fixture()
            value["questions"][0].update(type="score", options=[{"id": f"o{i}", "description": "", "value": score} for i, score in enumerate(scores)])
            value["state"]["ruleAnswers"] = {}
            repair_state(value)
            self.assertEqual(evaluate(encoded(value))["status"], "refused")

    def test_digest_mutations_bind_all_identities_and_array_order(self):
        baseline = fixture()
        original = validate_request(encoded(baseline))
        response = evaluate(encoded(baseline))
        for key in ("requestId", "stateDigest", "backendId", "capabilityId", "contextVersion", "policyId", "requestDigest", "questionsDigest", "modelManifestDigest", "policyDigest"):
            changed = deepcopy(response)
            changed[key] = "forged"
            changed["responseDigest"] = digest({k: v for k, v in changed.items() if k != "responseDigest"})
            with self.subTest(key=key), self.assertRaises(InvalidDecision):
                validate_response(changed, request=original)
        self.assertEqual(canonical({"b": 2, "a": 1}), canonical({"a": 1, "b": 2}))
        self.assertNotEqual(digest(["a", "b"]), digest(["b", "a"]))
        self.assertNotEqual(digest(-0.0), digest(0.0))

    def test_response_output_and_authority_forgery_fail_closed(self):
        value = fixture()
        request = validate_request(encoded(value))
        baseline = evaluate(encoded(value))
        for mutate in (lambda x: x.update(executionAuthorization=True),
                       lambda x: x.update(verified=True),
                       lambda x: x.update(grant={"executionAuthorization": True}),
                       lambda x: x.update(calibratedProbability=1),
                       lambda x: x.update(certificate={"verified": True}),
                       lambda x: x["answers"][0].update(pTrue=True),
                       lambda x: x["answers"][0].update(rawTopProbability=0.5),
                       lambda x: x["answers"][0]["distribution"][0].update(probability=-1),
                       lambda x: x.update(status="defer", reasonCodes=["overloaded"], inputCoverage=0),
                       lambda x: x["usage"].update(totalMs=float("inf"))):
            changed = deepcopy(baseline)
            mutate(changed)
            if changed["usage"]["totalMs"] != float("inf"):
                changed["responseDigest"] = digest({k: v for k, v in changed.items() if k != "responseDigest"})
            with self.assertRaises(InvalidDecision):
                validate_response(changed, request=request)
