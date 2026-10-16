# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit forecast namespace; default help/discovery never imports ML."""
from pathlib import Path
import json
import os
import stat
from .forecast_data import ForecastError,MAX_BYTES,parse_record

def add_parser(subparsers):
    parser=subparsers.add_parser('forecast',help='opt-in local numeric forecasts and heuristic advice')
    commands=parser.add_subparsers(dest='forecast_command',required=True)
    commands.add_parser('capabilities',help='discover without loading a model')
    server=commands.add_parser('serve-mcp',help='serve the separate local read-only stdio MCP transport')
    add_cpu_configuration(server)
    for command in ('predict','advice','inspect','export'):
        child=commands.add_parser(command,help='bounded explicit local '+command)
        child.add_argument('input',type=Path)
        if command=='predict':add_cpu_configuration(child)
        if command=='export':child.add_argument('--output',type=Path,required=True)

def add_cpu_configuration(parser):
    parser.add_argument('--cpu-manifest',type=Path,help='trusted operator launch configuration; never a tool argument')

def configured_session(args):
    from .forecast_advice import ForecastSession
    from .forecast_authority import DeploymentArtifactVerifier
    if args.cpu_manifest is None:return ForecastSession()
    manifest=read_input(args.cpu_manifest)
    verifier=DeploymentArtifactVerifier()
    verifier.verify(manifest)
    return ForecastSession(manifest,artifact_verifier=verifier)

def read_input(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno());
        if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_BYTES:raise ForecastError('input-budget-exceeded')
        return parse_record(stream.read(MAX_BYTES+1))

def run(args):
    from .forecast_advice import ForecastSession,capabilities
    from .forecast_store import verify_receipt,export_receipt
    try:
        if args.forecast_command=='capabilities':result=capabilities()
        elif args.forecast_command=='serve-mcp':
            from .forecast_mcp import main
            return main(session=configured_session(args))
        elif args.forecast_command=='predict':
            session=configured_session(args)
            try:result=session.predict(read_input(args.input))
            finally:session.close()
        elif args.forecast_command=='advice':
            from .forecast_policy import advise
            result=advise(read_input(args.input))
        else:
            result=verify_receipt(read_input(args.input))
            if args.forecast_command=='export':export_receipt(result,args.output)
            else:
                from .forecast_receipts import inspect_receipt
                result=inspect_receipt(result)
        print(json.dumps(result,sort_keys=True,allow_nan=False));return 0 if result.get('status') not in ('refused','unavailable','timed-out','cancelled') else 2
    except (ForecastError,OSError,ValueError,TypeError,KeyError):
        print(json.dumps({'status':'refused','reasonCodes':['forecast-request-refused'],'executionAuthorization':False}));return 2
