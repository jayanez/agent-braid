#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise the selected-flow driver with synthetic model packets, never ML/VM.

Actual collection is wired only by a separately frozen/admitted procedure. This
CLI has no command, engine or checkpoint argument and cannot enable that path.
"""
import argparse
from pathlib import Path


def simulated_collector(window, nonce):
    from agent_braid.forecast_baselines import predict_baseline
    from agent_braid.forecast_data import digest
    rows=[]
    for horizon in (1,5,1):
        forecast=predict_baseline(window,horizon,method='persistence')
        rows.append(dict(horizon=horizon,wallNs=forecast['costs']['wallNs'],forecast=forecast))
    manifest=rows[0]['forecast']['modelDigest']
    result=dict(version='agent-braid-selected-model-batch-v1',runNonce=nonce,
                sourceKind='synthetic-simulation',manifestDigest=manifest,inputDigest=digest(window),
                rows=rows,backendCalls=2,cacheHit=True,cleanupConfirmed=True,
                collectorDigest=digest({'collector':'simulation-only-v1'}),
                counterReceiptDigest=digest({'counters':'simulation-only-no-worker'}))
    result['receiptDigest']=digest(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic',action='store_true',help='Use simulated model packets; no ML or VM')
    parser.add_argument('--output-directory',type=Path)
    args=parser.parse_args()
    if not args.synthetic:
        print('No execution selected; actual collection requires a separately admitted package.')
        return 0
    if args.output_directory is None:parser.error('--synthetic requires --output-directory')
    import importlib.util
    spec=importlib.util.spec_from_file_location("owned_cost_driver",Path(__file__).with_name("reproduce_forecast_cost.py"))
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    package_digest=driver.package_digest
    from agent_braid.forecast_fullflow import run_selected_flow
    from agent_braid.runtime_policy import issue_operator_grant
    def operator(plan,root):return issue_operator_grant(plan,root,acknowledge=plan['planDigest'])
    return run_selected_flow(args.output_directory,collector=simulated_collector,operator=operator,
                             artifact_digest=package_digest(),source_kind='synthetic-simulation')


if __name__=='__main__':raise SystemExit(main())
