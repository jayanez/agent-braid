# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded synthetic descriptive overhead; no native host/provider or admission."""
from contextlib import redirect_stdout
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import platform
import statistics
import tempfile
import threading
import time
from unittest.mock import patch
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()

from agent_braid.cli import main
from agent_braid import tooling_telemetry as telemetry
from agent_braid.tooling_mcp import ToolingConfig, ToolingService

root=ROOT; fixture=root/'examples/analysis/file-edits.json';request=json.loads(fixture.read_text())
def summary(samples):
 ordered=sorted(samples)
 return dict(samples=len(samples),medianMs=statistics.median(samples),p95Ms=ordered[min(len(ordered)-1, int(len(ordered)*0.95))],minimumMs=min(samples),maximumMs=max(samples))
with tempfile.TemporaryDirectory() as temporary:
 base=Path(temporary).resolve(); directory=base/'metrics'; source=base/'source'; results=base/'results';source.mkdir();results.mkdir()
 output={}
 with patch.object(telemetry,'default_directory',return_value=directory):
  for surface,count in [('cli',100),('mcp',64)]:
   samples={'off':[],'local':[]}
   services={mode: ToolingService(ToolingConfig(source, results, telemetry=mode)) for mode in ('off','local')}
   def run(mode):
    start=time.perf_counter_ns()
    if surface=='cli':
     with redirect_stdout(io.StringIO()):
      result=main(['analyze',str(fixture),'--telemetry',mode])
     assert result==0
    else:
     result=services[mode].invoke('analyze-work',{'kind':'aim','request':request},threading.Event())
     assert result['status']=='ok'
    return (time.perf_counter_ns()-start)/1e6
   for _ in range(5):
    run('off');run('local')
   for index in range(count):
    for mode in (('off','local') if index%2==0 else ('local','off')):
     samples[mode].append(run(mode))
   output[surface]={mode:summary(values) for mode,values in samples.items()}
   output[surface]['medianPairedAddedMs']=statistics.median(b-a for a,b in zip(samples['off'],samples['local']))
   output[surface]['ratioOfMedians']=statistics.median(samples['local'])/statistics.median(samples['off'])
 assert telemetry._known_failures==0
 output['storeBytesAfterCalls']=sum(p.stat().st_size for p in directory.iterdir())
output=dict(schema='agent-braid-local-telemetry-synthetic-overhead/v1',method='One owned AIM fixture, five warmups/mode/surface, alternating paired off/local calls in one process; CLI includes parser/rendering, MCP includes envelope generation and in-memory evidence inventory. Disk writes are real. No native host/provider, experiment or threshold/general performance claim.',environment=dict(python=platform.python_version(),system=platform.system(),machine=platform.machine(),sqlite='stdlib extension'),measurements=output,inputs={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [fixture,root/'agent_braid/tooling_telemetry.py',root/'agent_braid/cli.py',root/'agent_braid/tooling_mcp.py',Path(__file__).resolve()]},limits=['Local uncontrolled synthetic descriptive timing only.','No native host, provider, production workload, independent reproduction or scientific utility evidence.','Warm measurements exclude module import; storage lock contention and stalled filesystem calls may add larger delays.'])
with arguments.output.open('x', encoding='utf-8') as stream:
 stream.write(json.dumps(output,indent=2)+'\n')
print(json.dumps(output['measurements'],indent=2))
