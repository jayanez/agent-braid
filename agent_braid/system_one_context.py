# SPDX-License-Identifier: AGPL-3.0-only
"""Immutable synthetic AIM context and explicitly bound diagnostic advice."""
from time import monotonic_ns
from agent_braid.system_one import (MAX_BYTES, HASH, MODEL_MANIFEST, CancellationToken,
    InvalidDecision, canonical, digest, freeze, thaw, parse_json, validate_request,
    validate_response, evaluate, policy_manifest)

class InvalidContext(ValueError):
    """Fixed, sanitized context refusal."""
    def __init__(self, code="invalid-context"):
        self.code = code
        super().__init__(code)

def keys(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise InvalidContext()

def identifier(value):
    if type(value) is not str or not value or len(value.encode("utf-8")) > 64 or any(ord(c)<32 or 0xD800<=ord(c)<=0xDFFF for c in value):
        raise InvalidContext()
    return value

def pin(value):
    if type(value) is not str or HASH.fullmatch(value) is None:
        raise InvalidContext()
    return value

def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise InvalidContext()
    return value

def validate_snapshot(value):
    """Preserve all AIM channels and input order; certify no declared effect."""
    keys(value, ('sourceKind','generation','operations'))
    if value['sourceKind'] != 'synthetic':
        raise InvalidContext('unsupported-source')
    integer(value['generation'],0,2**63-1)
    operations=value['operations']
    if type(operations) is not list or not 1<=len(operations)<=64:
        raise InvalidContext()
    from agent_braid.analysis import _validate_batch, InvalidAnalysis
    try:
        _validate_batch(operations)
        for op in operations:
            identifier(op['instanceId']); identifier(op['attemptId'])
    except (InvalidAnalysis, UnicodeError, TypeError, KeyError):
        raise InvalidContext() from None
    return freeze(value)

def validate_context(raw, *, expected_context_digest):
    try:
        value=parse_json(raw)
        if len(canonical(value))>MAX_BYTES:
            raise InvalidContext('wrapper-budget-exceeded')
        keys(value,('contractVersion','sourceKind','stage','generation','operations','decisionRequestDigest'))
        if value['contractVersion']!='s1-integration-synthetic-v1':
            raise InvalidContext()
        if value['stage']!='diagnostic':
            raise InvalidContext('unsupported-stage')
        pin(value['decisionRequestDigest']); pin(expected_context_digest)
        snapshot=validate_snapshot({k:value[k] for k in ('sourceKind','generation','operations')})
        if digest(value)!=expected_context_digest:
            raise InvalidContext('context-pin-mismatch')
        return freeze(value)
    except (InvalidDecision, UnicodeError, TypeError, OverflowError):
        raise InvalidContext() from None

def _packet(status, reason, *, context=None, original=None, delegated=None, response=None):
    value={'contractVersion':'s1-integration-synthetic-v1','status':status,
        'contextDigest':digest(context) if context is not None else None,
        'generation':context['generation'] if context is not None else None,
        'decisionRequestDigest':digest(original.envelope) if original else None,
        'delegatedRequestDigest':digest(delegated.envelope) if delegated else None,
        'delegatedDeadlineMs':delegated.budgets.deadline_ms if delegated else None,
        'decisionResponse':response,'stage':'diagnostic','operationIds':[o['instanceId'] for o in context['operations']] if context is not None else [],
        'fallback':'keep-original-order-and-run-existing-verifier','evidenceClass':'heuristic',
        'executionAuthorization':False,'reasonCodes':list(response['reasonCodes']) if response is not None else [] if reason is None else [reason]}
    value['packetDigest']=digest(value)
    return freeze(value)

def _advise_synthetic(context_bytes, decision_bytes, *, expected_context_digest,
                     expected_model_digest, expected_policy_digest, token, child, started):
    """Return synthetic fixture advice only; original/delegated requests remain bound."""
    deadline=started+5_000_000_000
    context=original=delegated=None
    def stopped():
        return 'cancelled' if token.cancelled else 'deadline-exceeded' if monotonic_ns()>=deadline else None
    try:
        if type(context_bytes) is not bytes or type(decision_bytes) is not bytes:
            raise InvalidContext()
        if len(context_bytes)+len(decision_bytes)>MAX_BYTES:
            raise InvalidContext('wrapper-budget-exceeded')
        if stopped(): return _packet('defer',stopped())
        context=validate_context(context_bytes,expected_context_digest=expected_context_digest)
        original=validate_request(decision_bytes)
        deadline=min(deadline,started+original.budgets.deadline_ms*1_000_000)
        if context['decisionRequestDigest']!=digest(original.envelope):
            raise InvalidContext('request-pin-mismatch')
        if pin(expected_model_digest)!=digest(MODEL_MANIFEST) or pin(expected_policy_digest)!=digest(policy_manifest(original.envelope['policyId'])):
            raise InvalidContext('manifest-pin-mismatch')
        remaining=(deadline-monotonic_ns())//1_000_000
        if stopped() or remaining<1:
            return _packet('defer',stopped() or 'deadline-exceeded',context=context,original=original)
        value=original.to_dict(); value['budgets']['deadlineMs']=min(value['budgets']['deadlineMs'],remaining)
        delegated=validate_request(canonical(value))
        response=evaluate(delegated.canonical_bytes,cancellation=child)
        # Core raw ingress is its canonical delegated copy, not the original bytes.
        validate_response(response,request=delegated)
        status='diagnostic' if response['status']=='answered' else response['status']
        packet=_packet(status,None,context=context,original=original,delegated=delegated,response=response)
        if len(canonical(packet))>MAX_BYTES:
            raise InvalidContext('wrapper-budget-exceeded')
        def publish(cancelled):
            reason='cancelled' if cancelled else stopped()
            return _packet('defer',reason,context=context,original=original,delegated=delegated) if reason else packet
        return token.publish(publish)
    except (InvalidContext,InvalidDecision) as exc:
        code=exc.code if isinstance(exc,InvalidContext) else 'invalid-context'
        return _packet('refused',code)
    except (ValueError,TypeError,UnicodeError,OverflowError):
        return _packet('refused','invalid-context')


def advise_synthetic(context_bytes, decision_bytes, *, expected_context_digest,
                     expected_model_digest, expected_policy_digest, cancellation=None):
    """Own one wrapper token scope and relay cancellation to isolated core scope."""
    started=monotonic_ns()
    token=cancellation if cancellation is not None else CancellationToken()
    if type(token) is not CancellationToken:
        return _packet('refused','invalid-context')
    try:
        token.claim()
    except ValueError:
        return _packet('refused','invalid-context')
    child=CancellationToken()
    remove=token.add_waker(child.cancel)
    try:
        if token.cancelled: child.cancel()
        return _advise_synthetic(context_bytes,decision_bytes,
            expected_context_digest=expected_context_digest,
            expected_model_digest=expected_model_digest,
            expected_policy_digest=expected_policy_digest,token=token,child=child,started=started)
    finally:
        remove(); token.release()
