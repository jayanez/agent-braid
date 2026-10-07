# SPDX-License-Identifier: AGPL-3.0-only
"""Separate bounded advice-only MCP stdio host; no runtime execution tools."""
from __future__ import annotations

from collections import deque
import json
import sys
import threading

from .system_one import (MAX_BYTES, InvalidDecision, canonical, digest, freeze, parse_json, thaw)
from ._advice_scope import _TransportScopeRegistry, InvalidAdviceScope, _scope_checkpoint

PROTOCOL = '2025-11-25'
TOOLS = ('s1_advice_capabilities', 's1_advise_stage')


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def _refusal(reason, *, status='refused', bound=None):
    value = {'contractVersion': 's1-stage-advice-v1', 'requestId': None,
        'requestDigest': None, 'contextDigest': None, 'generation': None,
        'registryDigest': None, 'stage': None, 'status': status, 'advice': None,
        'fallback': 'keep-original-order-and-use-existing-consumer',
        'reasonCodes': [reason], 'usage': {'validationMs': 0.0, 'ruleMs': 0.0,
            'totalMs': 0.0, 'inputBytes': 0, 'candidateCount': 0},
        'evidenceClass': 'heuristic', 'executionAuthorization': False}
    if bound is not None and bound.get('contractVersion') == 's1-stage-advice-v1':
        for key in ('requestId','requestDigest','contextDigest','generation','registryDigest','stage','usage'):
            value[key] = thaw(bound[key])
    value['packetDigest'] = digest(value)
    return freeze(value)


def advice_tool_catalog():
    """Fresh independent schemas; never aliases the legacy execution catalogue."""
    hash_schema = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    request = _object({'contractVersion': {'const': 's1-stage-advice-v1'},
        'requestId': {'type': 'string', 'minLength': 1, 'maxLength': 64},
        'context': _object({'sourceKind': {'const': 'synthetic'},
            'generation': {'type': 'integer', 'minimum': 0, 'maximum': 2**63-1},
            'operations': {'type': 'array', 'minItems': 1, 'maxItems': 64,
                           'items': AIM_SCHEMA}}),
        'contextDigest': hash_schema, 'registryDigest': hash_schema,
        'stage': {'enum': ['candidate-priority', 'analyzer-choice', 'effect-review',
                          'shortlist', 'adequacy', 'triage', 'ready-rank']},
        'payload': {'type': 'object'},
        'budgets': _object({'maxInputBytes': {'type': 'integer', 'minimum': 1, 'maximum': MAX_BYTES},
                           'maxCandidates': {'type': 'integer', 'minimum': 1, 'maximum': 64},
                           'deadlineMs': {'type': 'integer', 'minimum': 1, 'maximum': 5000}})})
    identifier = {'type':'string','minLength':1,'maxLength':64}
    ids = {'type':'array','maxItems':64,'uniqueItems':True,'items':identifier}
    names = {**ids,'maxItems':32}
    hint = _object({'candidateId':identifier,'rulePriority':{'type':'integer','minimum':0,'maximum':63}})
    hints = {'type':'array','maxItems':64,'items':hint}
    effect = _object({'kind':{'enum':['read','write','call','transform','emit','delete','deploy','unknown']},'resource':{'type':'string','minLength':1,'maxLength':MAX_BYTES}})
    effects = {'type':'array','maxItems':64,'items':effect}
    coverage = {'enum':['complete','partial','unknown']}
    comparison = _object({'comparisonId':identifier,'declared':effects,'observed':effects,'declaredCoverage':coverage,'observedCoverage':coverage})
    entry = _object({'entryId':identifier,'kind':{'enum':['tool-metadata','model-metadata','reference-rule']},'capabilities':names,'requiredArgumentNames':names,'allowedArgumentNames':names,'manifestDigest':hash_schema})
    category = _object({'caseId':identifier,'category':{'enum':['needs-review','unknown','counterexample-candidate']}})
    payloads = {
        'candidate-priority':_object({'domain':{'enum':['spec018-prefiltered','spec012-prefiltered']},'eligibleIds':ids,'hints':hints}),
        'analyzer-choice':_object({'populationIds':ids,'analysisBudgetDigest':hash_schema,'availableAnalyzerIds':names}),
        'effect-review':_object({'comparisons':{'type':'array','minItems':1,'maxItems':64,'items':comparison}}),
        'shortlist':_object({'registryEntries':{'type':'array','maxItems':32,'items':entry},'requestedCapabilities':names,'argumentNames':names}),
        'adequacy':_object({'requiredFields':names,'presentFields':names,'schemaDigest':hash_schema,'expectedSchemaDigest':hash_schema,'rubric':{'const':'required-field-completeness-v1'}}),
        'triage':_object({'caseIds':ids,'categories':{'type':'array','maxItems':64,'items':category}}),
        'ready-rank':_object({'readyIds':ids,'hints':hints,'readySetDigest':hash_schema,'schedulerConstraintsDigest':hash_schema,'grantBindingDigest':hash_schema})}
    request['oneOf'] = [{'properties':{'stage':{'const':name},'payload':schema}}
                        for name,schema in payloads.items()]
    request['properties']['payload'] = {'oneOf':list(payloads.values())}
    stage = _object({'request': request, 'expectedContextDigest': hash_schema,
                     'expectedRegistryDigest': hash_schema})
    nullable_hash = {'oneOf':[hash_schema,{'type':'null'}]}
    nullable_id = {'oneOf':[identifier,{'type':'null'}]}
    packet = _object({'contractVersion':{'const':'s1-stage-advice-v1'},
        'requestId':nullable_id,'requestDigest':nullable_hash,'contextDigest':nullable_hash,
        'generation':{'type':['integer','null'],'minimum':0,'maximum':2**63-1},
        'registryDigest':nullable_hash,'stage':{'enum':list(payloads)+[None]},
        'status':{'enum':['advised','unavailable','refused','defer']},
        'advice':{'type':['object','null']},
        'fallback':{'const':'keep-original-order-and-use-existing-consumer'},
        'reasonCodes':{'type':'array','maxItems':8,'items':{'enum':[
            'invalid-stage-request','unsupported-stage','unsupported-source',
            'context-pin-mismatch','registry-pin-mismatch','identity-set-mismatch',
            'unknown-metadata','unsupported-metadata','stage-budget-exceeded',
            'cancelled','deadline-exceeded','overloaded']}},
        'usage':_object({'validationMs':{'type':'number','minimum':0},'ruleMs':{'type':'number','minimum':0},
                        'totalMs':{'type':'number','minimum':0},'inputBytes':{'type':'integer','minimum':0,'maximum':MAX_BYTES},
                        'candidateCount':{'type':'integer','minimum':0,'maximum':64}}),
        'evidenceClass':{'const':'heuristic'},'executionAuthorization':{'const':False},'packetDigest':hash_schema})
    advice_schemas = {
        'candidate-priority':_object({'orderedIds':ids,'inputSetDigest':hash_schema,'rule':{'const':'stable-priority-v1'}}),
        'analyzer-choice':_object({'analyzerId':{'const':'exact-resource-footprints-v1'},'populationDigest':hash_schema,'analysisBudgetDigest':hash_schema}),
        'effect-review':_object({'comparisons':{'type':'array','maxItems':64,'items':_object({**comparison['properties'],'relation':{'enum':['equal','different','unknown']}})}}),
        'shortlist':_object({'entryIds':names,'excludedIds':{'type':'array','maxItems':32,'items':_object({'entryId':identifier,'reason':{'enum':['capability-missing','argument-shape-mismatch']}})}}),
        'adequacy':_object({'presentRequiredCount':{'type':'integer','minimum':0,'maximum':32},'requiredCount':{'type':'integer','minimum':1,'maximum':32},'missingFields':names,'schemaMatched':{'const':True}}),
        'triage':_object({'categories':{'type':'array','maxItems':64,'items':category}}),
        'ready-rank':_object({'orderedReadyIds':ids,'readySetDigest':hash_schema,'schedulerConstraintsDigest':hash_schema,'grantBindingDigest':hash_schema})}
    packet['oneOf'] = [{'properties':{'status':{'enum':['refused','defer','unavailable']},'advice':{'type':'null'}}}]+[
        {'properties':{'status':{'const':'advised'},'stage':{'const':name},'advice':schema}}
        for name,schema in advice_schemas.items()]
    capabilities = _object({'version': {'const': 's1-stage-registry-v1'},
        'registryDigest': hash_schema, 'stages': {'type': 'array', 'items': {'enum':list(payloads)}},
        'limits': _object({'maxInputBytes':{'const':MAX_BYTES},'maxCandidates':{'const':64},'deadlineMs':{'const':5000}}),
        'executionAuthorization': {'const': False}})
    return [{'name': TOOLS[0], 'description': 'Discover installed static synthetic advice rules.',
             'inputSchema': _object({}), 'outputSchema': capabilities,
             'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False}},
            {'name': TOOLS[1], 'description': 'Return bounded synthetic metadata advice.',
             'inputSchema': stage, 'outputSchema': packet,
             'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False}}]


class AdviceTools:
    def capabilities(self):
        from .system_one_advisors import stage_capabilities
        return stage_capabilities()

    def advise(self, scope):
        from .system_one_advisors import _advise_stage_in_scope
        return _advise_stage_in_scope(scope)


class AdviceStdioServer:
    """One active/eight waiting; all results are bounded before write-begin.

    Reader and writer blocking are outside hard termination claims. Methods do not
    launch clients, evaluate source code or call any execution/verifier/provider.
    """
    def __init__(self, output, *, _clock=None):
        self.output = output
        self.tools = AdviceTools()
        self._registry = (_TransportScopeRegistry() if _clock is None
                          else _TransportScopeRegistry(clock=_clock))
        self._output_lock = threading.Lock()
        self._condition = threading.Condition()
        self._session_ids = set()
        self._waiting = deque()
        self._active = None
        self._thread = None
        self.initializing = False
        self.initialized = False
        self.closed = False

    def _encoded(self, identifier, value):
        value = thaw(value)
        result = {'content': [{'type': 'text', 'text': canonical(value).decode('utf-8')}],
                  'structuredContent': value,
                  'isError': value.get('status') in {'refused', 'defer'}}
        payload = {'jsonrpc': '2.0', 'id': identifier, 'result': result}
        raw = canonical(payload)
        if len(raw) > MAX_BYTES:
            value = thaw(_refusal('stage-budget-exceeded',bound=value))
            payload['result'] = {'content': [{'type': 'text', 'text': canonical(value).decode()}],
                                 'structuredContent': value, 'isError': True}
            raw = canonical(payload)
        return raw + b'\n'

    def _write_bytes(self, raw):
        # A scoped writer has already won its atomic write-begin boundary.
        self.output.write(raw)
        self.output.flush()

    def _plain(self, value):
        raw = canonical(value)
        if len(raw) > MAX_BYTES:
            raw = canonical({'jsonrpc':'2.0', 'id':value.get('id'),
                             'error':{'code':-32603,'message':'response-limit'}})
        with self._output_lock:
            if not self.closed:
                self._write_bytes(raw + b'\n')

    def _error(self, identifier, code):
        messages = {-32700:'invalid-json', -32600:'invalid-request', -32601:'unknown-method',
                    -32602:'invalid-parameters'}
        self._plain({'jsonrpc':'2.0','id':identifier,
                     'error':{'code':code,'message':messages[code]}})

    @staticmethod
    def _id(identifier):
        return ((type(identifier) is int and -(2**63) <= identifier < 2**63)
                or (type(identifier) is str and 1 <= len(identifier.encode('utf-8')) <= 64
                    and not any(ord(c)<32 or 127<=ord(c)<=159 for c in identifier)))

    def receive(self, raw):
        if self.closed:
            return
        try:
            ticket = self._registry.begin_ingress()
        except InvalidAdviceScope:
            return
        try:
            try:
                frame = parse_json(raw)
            except InvalidDecision:
                self._error(None, -32700)
                return
            identifier = frame.get('id')
            if (set(frame) - {'jsonrpc','id','method','params'} or frame.get('jsonrpc')!='2.0'
                    or type(frame.get('method')) is not str
                    or ('id' in frame and not self._id(identifier))):
                self._error(None, -32600)
                return
            notification = 'id' not in frame
            if not notification:
                with self._condition:
                    identity = (type(identifier),identifier)
                    denied = identity in self._session_ids or len(self._session_ids) >= 1024
                    if not denied:self._session_ids.add(identity)
                if denied:
                    self._error(identifier,-32600)
                    return
            method, params = frame['method'], frame.get('params', {})
            if type(params) is not dict:
                if not notification:
                    self._error(identifier,-32602)
                return
            if notification:
                if method == 'notifications/initialized' and params == {} and self.initializing and not self.initialized:
                    self.initialized = True
                elif method == 'notifications/cancelled':
                    if (set(params) <= {'requestId','reason'} and self._id(params.get('requestId'))
                            and ('reason' not in params or (type(params['reason']) is str
                                 and len(params['reason'].encode()) <= 256))):
                        self._cancel_request(params['requestId'])
                return
            if method == 'initialize':
                if (self.initializing or set(params) != {'protocolVersion','capabilities','clientInfo'}
                        or params.get('protocolVersion') != PROTOCOL
                        or type(params.get('capabilities')) is not dict
                        or type(params.get('clientInfo')) is not dict
                        or set(params['clientInfo']) != {'name','version'}
                        or any(type(params['clientInfo'][k]) is not str for k in ('name','version'))):
                    self._error(identifier,-32602)
                    return
                self.initializing = True
                self._plain({'jsonrpc':'2.0','id':identifier,'result':{'protocolVersion':PROTOCOL,
                    'capabilities':{'tools':{}}, 'serverInfo':{'name':'agent-braid-system-one-advice',
                                                           'version':'s1-integration-synthetic-v1'}}})
                return
            if method not in {'tools/list','tools/call'}:
                self._error(identifier,-32601)
                return
            if not self.initialized:
                self._error(identifier,-32602)
                return
            if method=='tools/list':
                if params:
                    self._error(identifier,-32602)
                else:
                    self._plain({'jsonrpc':'2.0','id':identifier,'result':{'tools':advice_tool_catalog()}})
                return
            if (set(params) != {'name','arguments'} or params.get('name') not in TOOLS
                    or type(params.get('arguments')) is not dict):
                self._error(identifier,-32602)
                return
            name, args = params['name'], params['arguments']
            if name == TOOLS[0]:
                if args:
                    self._error(identifier,-32602)
                    return
                request_bytes = canonical({'capabilities':{}})
                context_pin = registry_pin = None
            else:
                if set(args) != {'request','expectedContextDigest','expectedRegistryDigest'}:
                    self._error(identifier,-32602)
                    return
                try:
                    from .system_one_advisors import validate_stage_request
                    request_bytes = canonical(args['request'])
                    context_pin, registry_pin = args['expectedContextDigest'], args['expectedRegistryDigest']
                    validate_stage_request(request_bytes,expected_context_digest=context_pin,
                                           expected_registry_digest=registry_pin)
                except (ValueError,TypeError,KeyError,OverflowError):
                    self._error(identifier,-32602)
                    return
            try:
                scope = self._registry.admit(ticket,identifier,request_bytes,
                    expected_context_digest=context_pin,expected_registry_digest=registry_pin,
                    stage=name == TOOLS[1])
            except (InvalidAdviceScope,InvalidDecision):
                self._error(identifier,-32600)
                return
            overloaded = False
            with self._condition:
                if self.closed:
                    self._registry.complete(scope)
                    return
                if self._active is not None:
                    if len(self._waiting) == 8:
                        overloaded = True
                    else:
                        self._waiting.append((scope,name,identifier))
                else:
                    self._active = scope
                    self._thread = threading.Thread(target=self._run,args=((scope,name,identifier),),
                                                    daemon=True,name='braid-advice-only')
                    self._thread.start()
            if overloaded:
                try:self._publish(scope,self._scope_refusal(scope,'overloaded',status='defer'))
                finally:self._registry.complete(scope)
        finally:
            self._registry.discard_ingress(ticket)

    def _scope_refusal(self, scope, reason, *, status='refused'):
        if not scope.stage:
            return _refusal(reason,status=status)

        try:
            from .system_one_advisors import validate_stage_request
            request=validate_stage_request(scope.request_bytes,
                expected_context_digest=scope.expected_context_digest,
                expected_registry_digest=scope.expected_registry_digest)
            value=request.to_dict()
            bound={'contractVersion':'s1-stage-advice-v1','requestId':value['requestId'],
                'requestDigest':scope.request_digest,'contextDigest':value['contextDigest'],
                'generation':value['context']['generation'],'registryDigest':value['registryDigest'],
                'stage':value['stage'],'usage':{'validationMs':0.0,'ruleMs':0.0,
                    'totalMs':max(0,(self._registry._clock()-scope.ingress_started_ns)/1e6),
                    'inputBytes':len(scope.request_bytes),'candidateCount':request.candidate_count}}
            return _refusal(reason,status=status,bound=bound)
        except (ValueError,TypeError,KeyError,OverflowError):
            return _refusal(reason,status=status)

    def _cancel_request(self, identifier):
        removed = None
        typed_id = (type(identifier),identifier)
        with self._condition:
            for entry in self._waiting:
                if entry[0].request_id == typed_id:
                    self._waiting.remove(entry)
                    removed = entry[0]
                    break
        if removed is None:
            self._registry.cancel(identifier)
        else:
            removed.cancellation.cancel()
            self._registry.complete(removed)

    def _publish(self, scope, value):
        raw = self._encoded(scope.request_id[1],value)
        with self._output_lock:
            self._registry.publish(scope,lambda:self._write_bytes(raw))

    def _run(self, entry):
        while entry is not None:
            scope,name,identifier = entry
            try:
                if _scope_checkpoint(scope) != 'live':
                    value = None
                elif name == TOOLS[0]:
                    value = self.tools.capabilities()
                else:
                    value = self.tools.advise(scope)
            except Exception:
                # No collaborator exception, rejected text or stack reaches the wire.
                value = None
            try:
                if value is not None:
                    try:
                        self._publish(scope,value)
                    except (ValueError,TypeError,KeyError,OverflowError):
                        pass
            except (BrokenPipeError,OSError):
                self.close()
            finally:
                self._registry.complete(scope)
            with self._condition:
                entry = self._waiting.popleft() if self._waiting and not self.closed else None
                self._active = None if entry is None else entry[0]
                self._condition.notify_all()

    def wait_idle(self, timeout=5):
        with self._condition:
            return self._condition.wait_for(lambda:self._active is None,timeout=timeout)

    def close(self):
        # Mark both server and registry closed under the publication-state lock.
        # Token cancellation occurs only after releasing this registry lock.
        with self._registry._lock:
            self.closed = True
            self._registry._closed = True
        self._registry.close()
        with self._condition:
            waiting = list(self._waiting)
            self._waiting.clear()
        for scope,_,_ in waiting:
            self._registry.complete(scope)

    def serve(self, source):
        try:
            while not self.closed:
                line = source.readline(MAX_BYTES+2)
                if not line:
                    break
                raw = line[:-1] if line.endswith(b'\n') else line
                if len(raw)>MAX_BYTES:
                    while line and not line.endswith(b'\n'):
                        line=source.readline(MAX_BYTES+2)
                    self._error(None,-32700)
                    continue
                self.receive(raw)
            self.wait_idle()
        finally:
            self.close()


def main():
    AdviceStdioServer(sys.stdout.buffer).serve(sys.stdin.buffer)


# Static schema bytes are embedded at engineering time; no runtime source reads.
AIM_SCHEMA = {'title': 'Agent Braid agent-interaction-metadata 0.2.0-draft', 'type': 'object', 'additionalProperties': False, 'properties': {'aimVersion': {'const': '0.2.0-draft'}, 'instanceId': {'type': 'string', 'minLength': 1}, 'attemptId': {'type': 'string', 'minLength': 1}, 'definition': {'type': 'object', 'additionalProperties': False, 'properties': {'id': {'type': 'string', 'minLength': 1}, 'digest': {'type': 'string', 'pattern': '^sha256:[0-9a-f]{64}$'}}, 'required': ['id', 'digest']}, 'inputDigest': {'type': 'string', 'pattern': '^sha256:[0-9a-f]{64}$'}, 'dependencies': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'uniqueItems': True}, 'readVersions': {'type': 'object', 'additionalProperties': {'type': 'integer', 'minimum': 0}}, 'effects': {'type': 'object', 'additionalProperties': False, 'properties': {'declared': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'properties': {'kind': {'enum': ['read', 'write', 'call', 'transform', 'emit', 'delete', 'deploy', 'unknown']}, 'resource': {'type': 'string', 'minLength': 1}}, 'required': ['kind', 'resource']}}, 'inferred': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'properties': {'kind': {'enum': ['read', 'write', 'call', 'transform', 'emit', 'delete', 'deploy', 'unknown']}, 'resource': {'type': 'string', 'minLength': 1}}, 'required': ['kind', 'resource']}}, 'observed': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'properties': {'kind': {'enum': ['read', 'write', 'call', 'transform', 'emit', 'delete', 'deploy', 'unknown']}, 'resource': {'type': 'string', 'minLength': 1}}, 'required': ['kind', 'resource']}}, 'coverage': {'type': 'object', 'additionalProperties': False, 'properties': {'status': {'enum': ['complete', 'partial', 'unknown']}, 'domain': {'type': 'string', 'minLength': 1}, 'method': {'type': 'string', 'minLength': 1}}, 'required': ['status', 'domain', 'method']}}, 'required': ['declared', 'inferred', 'observed', 'coverage']}, 'evidence': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'properties': {'property': {'enum': ['terminal-observation-equivalence', 'independence', 'confluence', 'braid']}, 'method': {'enum': ['declared', 'replay', 'exhaustive-finite', 'proof-rule', 'formal']}, 'domain': {'type': 'string', 'minLength': 1}, 'assumptions': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}}, 'observationContract': {'type': 'string', 'minLength': 1}, 'executionContract': {'type': 'string', 'minLength': 1}, 'assuranceClass': {'type': 'integer', 'minimum': 0, 'maximum': 5}}, 'required': ['property', 'method', 'domain', 'assumptions', 'observationContract', 'executionContract', 'assuranceClass']}, 'minItems': 1}}, 'required': ['aimVersion', 'instanceId', 'attemptId', 'definition', 'inputDigest', 'dependencies', 'readVersions', 'effects', 'evidence']}

if __name__ == '__main__':
    main()
