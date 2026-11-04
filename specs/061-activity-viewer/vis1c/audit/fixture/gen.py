import json
seq=0; out=[]
def ev(kind,t,data,host="braid",adapter="viewer",ref=None,ver="derived",cls=None,basis="artifact-relative"):
    global seq; seq+=1
    out.append({"assurance":{"compatibilityClass":cls,"notAGuarantee":True},"at":{"basis":basis,"relMs":t},"data":data,
      "executionAuthorization":False,"kind":kind,"schemaVersion":"agent-braid-loom/v0.1","seq":seq,
      "source":{"adapter":adapter,"evidenceRef":ref,"host":host,"verification":ver}})
R={"path":"runs/demo/analysis.json","sha256":"a"*64}
def op(t,sid,label,host,role,parent=None,adapter="claude-hook",ver="unverified",ref=None):
    ev("strand.open",t,{"host":host,"label":label,"parentStrandId":parent,"role":role,"strandId":sid},host=host,adapter=adapter,ver=ver,ref=ref)
ev("session.origin",0,{"hosts":["braid","claude","codex"],"limits":{"crossings":4096,"events":50000,"grants":1024,"strands":256,"waves":64},"mode":"replay"})
op(1000,"main","Claude main session","claude","agent")
op(8000,"explore","Explore: map viewer code","claude","subagent","main")
op(9000,"plan","Plan: redesign proposal","claude","subagent","main")
for t,s,tool in [(12000,"explore","Read"),(20000,"explore","Grep"),(31000,"plan","Read"),(47000,"explore","Bash")]:
    ev("strand.update",t,{"state":"running","strandId":s,"toolName":tool},host="claude",adapter="claude-hook",ver="unverified")
ev("strand.close",52000,{"outcome":"ok","strandId":"explore"},host="claude",adapter="claude-hook",ver="unverified")
ev("strand.close",95000,{"outcome":"ok","strandId":"plan"},host="claude",adapter="claude-hook",ver="unverified")
# analysis of 3 operations from a braid plan
ev("analysis.report",100000,{"limits":["file-level resources only"],"operationCount":4,"pairCount":6,"reportId":"sha256:"+"a"*64,"summary":{"conflicting":1,"independentCandidate":2,"ordered":1,"unknown":2},"uncertainty":["unknown-script declares no effects"]},adapter="analysis-report",ref=R,ver="rehashed")
for sid,label,t in [("edit-readme","Edit README","110000"),("edit-roadmap","Edit ROADMAP","110500"),("edit-roadmap-2","Second ROADMAP edit","111000"),("unknown-script","Run unknown script","111500")]:
    op(int(t),sid,label,"braid","operation",adapter="analysis-report",ver="rehashed",ref=R)
def cx(t,l,r,c,cls,shared=(),cov=("complete",)):
    ev("crossing.classified",t,{"classification":c,"constraints":[],"evidence":{"coverage":list(cov),"method":"exact-resource-footprint","ruleSet":"demo-rules"},"left":l,"reasons":["demo"],"reportId":"sha256:"+"a"*64,"right":r,"sharedResources":list(shared)},adapter="analysis-report",ref=R,ver="rehashed",cls=cls)
cx(112000,"edit-readme","edit-roadmap","independent-candidate",1)
cx(112100,"edit-roadmap","edit-roadmap-2","conflicting",0,["file:ROADMAP.md"])
cx(112200,"edit-readme","unknown-script","unknown",0,[],["complete","unknown"])
cx(112300,"edit-readme","edit-roadmap-2","independent-candidate",2)
cx(112400,"edit-roadmap","unknown-script","ordered",3)
ev("wave.planned",113000,{"mode":"candidate-preparation-waves","planId":"sha256:"+"b"*64,"serialSlots":4,"waves":[["edit-readme","edit-roadmap"],["edit-roadmap-2"],["unknown-script"]]},adapter="git-replay-plan",ref=R,ver="rehashed")
ev("grant.issued",114000,{"action":"execute","derived":False,"grantId":"grant-1"},adapter="runtime-grant",ref=R,ver="rehashed")
ev("wave.started",115000,{"scheduleId":"sha256:"+"c"*64,"strands":["edit-readme","edit-roadmap"],"wave":0},adapter="scheduler-preparation",ref=R,ver="rehashed")
ev("wave.finished",180000,{"scheduleId":"sha256:"+"c"*64,"strands":["edit-readme","edit-roadmap"],"wave":0},adapter="scheduler-preparation",ref=R,ver="rehashed")
ev("strand.close",181000,{"outcome":"ok","strandId":"edit-readme"},adapter="runtime-state",ref=R,ver="rehashed")
ev("grant.consumed",182000,{"action":"execute","derived":False,"grantId":"grant-1"},adapter="runtime-grant",ref=R,ver="rehashed")
op(200000,"reviewer","Code reviewer","claude","subagent","main")
ev("effort.sample",205000,{"basis":"host-estimate","cacheCreationTokens":None,"cacheReadTokens":30000,"cachedInputTokens":None,"costUsd":0.12,"durationMs":None,"inputTokens":12000,"model":"example-model","outputTokens":900,"reasoningTokens":None,"strandId":"reviewer"},host="claude",adapter="otlp-logs",ver="unverified")
op(210000,"codex-t1","Codex thread","codex","agent",adapter="codex-hook")
ev("observation.gap",220000,{"fromSeq":None,"reason":"subagent-usage-unattributed","strandId":"codex-t1","toSeq":None})
ev("hazard.noticed",230000,{"hazardKind":"not-observed","stage":"receipt","units":["edit-roadmap-2"]},adapter="ownership-notice",ref=R,ver="rehashed")
ev("gate.result",240000,{"gateId":"gate-1","operationCount":4,"status":"hazards-found"},adapter="workflow-gate",ref=R,ver="rehashed",cls=0)
ev("strand.close",250000,{"outcome":"ok","strandId":"reviewer"},host="claude",adapter="claude-hook",ver="unverified")
ev("strand.close",262000,{"outcome":"unknown","strandId":"main"},host="claude",adapter="claude-hook",ver="unverified")
import sys
with open(sys.argv[1],"w") as f:
    for e in out: f.write(json.dumps(e,sort_keys=True,separators=(",",":"))+"\n")
