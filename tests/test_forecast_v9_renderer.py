# SPDX-License-Identifier: AGPL-3.0-only
"""Offline rendered-text contracts; no systemd validation or native providers."""
from dataclasses import replace
import hashlib
import json
import unittest
from unittest.mock import patch

from agent_braid.forecast_bootstrap import offline_bootstrap_v4
from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_v9_driver import offline_v9_plan, OfflineV9Integration
from agent_braid.forecast_v9_renderer import render_offline_v9
from tests.test_forecast_v9_driver import preparation, profile


def fields(text, section):
    active = False; values = {}
    for line in text.splitlines():
        if line.startswith('['): active = line == '['+section+']'
        elif active and '=' in line:
            key,value = line.split('=',1)
            values.setdefault(key,[]).append(value)
    return values


class RendererTests(unittest.TestCase):
    def test_exact_nine_units_no_mount_jobs_or_additional_service_activation(self):
        p = profile(); r = render_offline_v9(p)
        self.assertEqual(len(r['units']),9)
        self.assertEqual(sum(n.endswith('.service') for n in r['units']),6)
        self.assertEqual(sum(n.endswith('.slice') for n in r['units']),3)
        self.assertEqual(r['managerMountJobs'],[])
        self.assertEqual(r['explicitServiceActivationEdges'],[])
        self.assertEqual(set(r['roles']), {'supervisor','anchor','operator','prepare','verify','terminal'})
        for text in r['units'].values():
            unit=fields(text,'Unit')
            self.assertEqual(unit['DefaultDependencies'],['no'])
            self.assertNotIn('[Install]', text)
            self.assertNotIn('.mount', text)
            if '[Service]' in text:
                for key in ('Wants','BindsTo','Upholds','OnSuccess','OnFailure'):
                    self.assertNotIn(key,unit)
                self.assertEqual(unit['Requires'],fields(text,'Service')['Slice'])
        self.assertEqual(r['roles']['anchor'], 'fc1'+p.identity+'.service')

    def test_numeric_credentials_and_single_exec_match_patched_policy(self):
        r = render_offline_v9(profile())
        for role,name in r['roles'].items():
            values=fields(r['units'][name],'Service')
            uid = '0' if role in ('supervisor','anchor','operator') else '61001'
            self.assertEqual(values['User'],[uid]);self.assertEqual(values['Group'],[uid])
            self.assertEqual(values['SetLoginEnvironment'],['no'])
            self.assertEqual(values['Restart'],['no'])
            self.assertEqual(len(values['ExecStart']),1)
            self.assertEqual(values['Type'],['exec'])
            for key in ('ExecStartPre','ExecStartPost','ExecStop','ExecStopPost','ExecCondition','ExecReload','SystemCallFilter','PAMName'):
                self.assertNotIn(key,values)
            for key in ('StandardInput','StandardOutput','StandardError'):
                self.assertEqual(values[key],['null'])

    def test_worker_isolation_storage_paths_and_resource_caps_preserved(self):
        p=profile();r=render_offline_v9(p); old=p.units(remaining_seconds=50)
        keys=('Slice','RootImage','RootHash','BindPaths','BindReadOnlyPaths','WorkingDirectory',
              'PrivateNetwork','PrivateDevices',
              'NoNewPrivileges','CapabilityBoundingSet','ProtectSystem','InaccessiblePaths')
        for role in ('prepare','verify','terminal'):
            name=r['roles'][role]
            new=fields(r['units'][name],'Service'); prior=fields(old[name],'Service')
            for key in keys:
                self.assertEqual(new[key], prior[key], (role,key))
        self.assertFalse(any(n.endswith(('-grant.service','-dispatch.service')) for n in r['units']))
        for name in r['sliceParents']:
            self.assertEqual(fields(r['units'][name],'Slice'), fields(old[name],'Slice'))
        worker_slice='fc1'+p.identity+'-workers.slice'
        self.assertEqual(fields(r['units'][worker_slice],'Slice')['MemoryMax'],['2147483648'])
        self.assertEqual(fields(r['units'][worker_slice],'Slice')['TasksMax'],['64'])

    def test_timeouts_fit_existing_windows_and_tight_profile_refuses(self):
        p=profile();r=render_offline_v9(p)
        for role,name in r['roles'].items():
            values=fields(r['units'][name],'Service')
            total=sum(int(values[k][0]) for k in ('RuntimeMaxSec','TimeoutStartSec','TimeoutStopSec'))
            self.assertEqual(total,50 if role in ('supervisor','anchor','operator') else 30 if role=='prepare' else 10)
        short=replace(p,limits=tuple(replace(row,wall_seconds=3) for row in p.limits))
        with self.assertRaisesRegex(ForecastError,'start-stop-reserve'):render_offline_v9(short)

    def test_rendered_bytes_bound_through_graph_bootstrap_and_broker_identity(self):
        p=profile();prep=preparation();plan=offline_v9_plan(prep,p,100)
        r=plan['graph']['renderer']
        self.assertEqual(plan['bootstrap']['unitSha256'], r['unitSha256'])
        self.assertEqual(plan['bootstrap']['graphDigest'], digest(plan['graph']))
        for name,text in r['units'].items():
            self.assertEqual(r['unitSha256'][name],hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(r['unitSetDigest'],digest(r['unitSha256']))
        s=OfflineV9Integration(prep,p,100)
        self.assertEqual(s.broker.integration_identity,s.identity)
        self.assertEqual(s.receipt()['renderedUnitDigest'],r['unitSetDigest'])
        with patch('agent_braid.forecast_v9_renderer.render_offline_v9',return_value={**r,'rendererSha256':'a'*64}):
            changed=OfflineV9Integration(prep,p,100)
        self.assertNotEqual(s.identity,changed.identity)
        self.assertNotEqual(plan['bootstrap']['graphDigest'],json.loads(changed.plan_bytes)['bootstrap']['graphDigest'])
        detached=render_offline_v9(p);detached['units'].clear()
        self.assertEqual(render_offline_v9(p),r)

    def test_bootstrap_rejects_missing_extra_or_malformed_unit_pins(self):
        prep=preparation();r=render_offline_v9(profile())
        cases=[{}, {**r['unitSha256'],'extra.service':'a'*64},
               {**r['unitSha256'],r['roles']['anchor']:'bad'}]
        for pins in cases:
            with self.subTest(pins=len(pins)),self.assertRaises(ForecastError):
                offline_bootstrap_v4(prep,100,'c'*64,unit_sha256=pins)

    def test_rendering_never_changes_profile_or_closes_implicit_dependency_gates(self):
        p=profile();before=p.manifest();r=render_offline_v9(p)
        self.assertEqual(p.manifest(),before)
        self.assertEqual(before['version'],'agent-braid-linux-admission-profile-v8')
        self.assertEqual(r['profileBindingVersion'],before['version'])
        self.assertGreater(len(r['unresolvedDependencies']),0)
        for key in ('nativeGraphClosed','profileV9Emitted','operationalBudgetClosed','nativeQualification','executionAuthorization'):
            self.assertIs(r[key],False)
        s=OfflineV9Integration(preparation(),p,100)
        with patch('agent_braid.forecast_v9_driver.bootstrap_ready'):
            with self.assertRaisesRegex(ForecastError,'outer-guard-pending'):s.driver.native_entry(p)

    def test_receipt_rejects_replaced_rendered_plan_or_broker_binding(self):
        for field in ('plan','broker'):
            s=OfflineV9Integration(preparation(),profile(),100)
            if field=='plan': s.plan_bytes=b'{}'
            else: s.broker.integration_identity='a'*64
            with self.subTest(field=field),self.assertRaisesRegex(ForecastError,'rendered-plan-drift'):
                s.receipt()
            self.assertTrue(s.driver.failed and s.driver.escrow.failed)
