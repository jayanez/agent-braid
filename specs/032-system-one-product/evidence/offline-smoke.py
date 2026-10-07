from pathlib import Path
import hashlib,importlib,json,sys
import agent_braid
from agent_braid.system_one import canonical,digest,evaluate,validate_request,validate_response,MODEL_MANIFEST,policy_manifest,STRICT_POLICY,InvalidDecision
from agent_braid.system_one_schema import compile_schema,compiler_manifest
from agent_braid.system_one_router import router_registry_manifest,route_metadata
from agent_braid.system_one_hooks import ObservationBuffer
from agent_braid.system_one_advisors import stage_registry_manifest,stage_capabilities,advise_stage,validate_stage_packet
from agent_braid.system_one_context import advise_synthetic
from agent_braid.mcp_advice import advice_tool_catalog
from agent_braid.system_one_trace import StageObservationBuffer
origin=Path(agent_braid.__file__).resolve();assert origin.is_relative_to(Path(sys.prefix).resolve()) and 'site-packages' in origin.parts
bindings=json.loads(Path(sys.argv[1]).read_text())
for name,expected in bindings.items():
 module=importlib.import_module(name);p=Path(module.__file__).resolve();assert p.is_relative_to(Path(sys.prefix).resolve());assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,(name,'source mismatch')
raw=Path(sys.argv[2]).read_bytes()
request=validate_request(raw);response=evaluate(raw);assert response['status']=='answered' and response['executionAuthorization'] is False;validate_response(response,request=request)
strict=request.to_dict();strict['policyId']=STRICT_POLICY;assert evaluate(canonical(strict))['status']=='abstain'
forged=dict(response);forged['executionAuthorization']=True
try:validate_response(forged,request=request)
except InvalidDecision:pass
else:raise AssertionError('forged authority')
compiled=compile_schema(b'{"type":"boolean"}');assert compiled['questions'][0]['id']==digest({'instancePointer':'','schemaPointer':''});assert compiled['questions'][0]['type']=='boolean';assert compiled['executionAuthorization'] is False
registry=router_registry_manifest();route={'contractVersion':'s1-metadata-router-v1','requestId':'offline-route','sourceKind':'synthetic','languageTag':'es','taskId':'schema-compile-fixture','registryDigest':registry['digest'],'deadlineMs':5000}
routed=route_metadata(canonical(route),expected_registry_digest=registry['digest']);assert routed['status']=='matched' and routed['route']['installedManifestDigest']==digest(compiler_manifest()) and routed['executionAuthorization'] is False
buffer=ObservationBuffer(1);assert buffer.record(canonical(response),request_bytes=raw)['status']=='recorded';assert buffer.record(canonical(response),request_bytes=raw)['status']=='dropped';drained=buffer.drain();assert len(drained['records'])==1 and drained['droppedCount']==1;assert 'answers' not in drained['records'][0]
ops=json.loads(Path(sys.argv[3]).read_text())['operations'];context={'sourceKind':'synthetic','generation':0,'operations':ops};manifest=stage_registry_manifest();assert len(stage_capabilities()['stages'])==7
source=manifest['inventory']['sources'][0];analysis=importlib.import_module('agent_braid.analysis');assert source['moduleSourceDigest']==hashlib.sha256(Path(analysis.__file__).read_bytes()).hexdigest()
stage={'contractVersion':'s1-stage-advice-v1','requestId':'offline-stage','context':context,'contextDigest':digest(context),'registryDigest':digest(manifest),'stage':'triage','payload':{'caseIds':['x'],'categories':[{'caseId':'x','category':'unknown'}]},'budgets':{'maxInputBytes':1048576,'maxCandidates':64,'deadlineMs':5000}}
packet=advise_stage(canonical(stage),expected_context_digest=digest(context),expected_registry_digest=digest(manifest));assert packet['status']=='advised' and packet['executionAuthorization'] is False;validate_stage_packet(packet,request_bytes=canonical(stage),expected_context_digest=digest(context),expected_registry_digest=digest(manifest))
wrapper={'contractVersion':'s1-integration-synthetic-v1','sourceKind':'synthetic','stage':'diagnostic','generation':0,'operations':ops,'decisionRequestDigest':digest(request.envelope)}
wrapped=advise_synthetic(canonical(wrapper),raw,expected_context_digest=digest(wrapper),expected_model_digest=digest(MODEL_MANIFEST),expected_policy_digest=digest(policy_manifest(request.envelope['policyId'])));assert wrapped['status']=='diagnostic' and wrapped['executionAuthorization'] is False
trace=StageObservationBuffer(1);cost={'adviceMs':packet['usage']['totalMs'],'fallbackMs':None,'verifierMs':None,'runtimeMs':None,'totalMs':None};assert trace.record(canonical(packet),request_bytes=canonical(stage),expected_context_digest=digest(context),expected_registry_digest=digest(manifest),cost=cost)['status']=='recorded';trace_row=trace.drain()['records'][0];assert trace_row['cost']['totalMs'] is None and 'operationIds' not in trace_row
assert len(advice_tool_catalog())==2
assert not any(name in sys.modules for name in ('torch','transformers','openai','onnxruntime','requests'))
print(json.dumps({'offlineInstalledSelectedSubset':'passed','python':sys.version.split()[0],'sourceOrigin':'fresh-isolated-site-packages','sourceModulesCompared':len(bindings),'strictAbstention':'passed','syntheticDiagnostic':'passed','compiler':'passed','declaredRouter':'passed','observationPrivacyOverflow':'passed','stageRegistrySourcePins':'passed','pureStageValidation':'passed','stageTelemetryPrivacy':'passed','syntheticWrapper':'passed','legacyAuthority':'unchanged','optionalModelPackagesLoaded':False,'humanReview':'pending','executionAuthorization':False},sort_keys=True))
