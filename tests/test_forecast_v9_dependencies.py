# SPDX-License-Identifier: AGPL-3.0-only
"""Pure text/edge checks over owned fixtures; no manager, mounts or workloads."""
import unittest

from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_v9_driver import OfflineV9Integration, offline_v9_plan
from agent_braid.forecast_v9_renderer import render_offline_v9, offline_dependency_inventory
from tests.test_forecast_v9_driver import preparation, profile


class DependencyTests(unittest.TestCase):
    def test_service_slice_edges_are_explicit_and_only_root_slice_is_external(self):
        r=render_offline_v9(profile()); d=r['dependencyInventory']
        self.assertEqual(d['serviceSliceEdgesPromoted'],12)
        self.assertEqual(len(d['explicitEdges']),23)
        self.assertEqual({e['to'] for e in d['explicitEdges'] if not e['local']},{'-.slice'})
        for role,name in r['roles'].items():
            target='fc1'+profile().identity+('-root.slice' if role in
                ('supervisor','anchor','operator') else '-workers.slice')
            for kind in ('Requires','After'):
                self.assertIn({'from':name,'kind':kind,'to':target,'local':True},d['explicitEdges'])

    def test_paths_remain_obligations_and_ordering_is_not_service_activation(self):
        r=render_offline_v9(profile());d=r['dependencyInventory']
        for directive in ('RootImage','WorkingDirectory'):
            self.assertEqual(sum(row['directive']==directive for row in d['pathResolutionObligations']),3)
        self.assertEqual(len(d['rootImageOrderingObligations']),3)
        self.assertTrue(all(e['kind']=='After' and e['to']=='systemd-udevd.service' and
                            e['activationByThisEdge'] is False for e in d['rootImageOrderingObligations']))
        self.assertGreater(len(d['blockers']),0)
        for key in ('offlineClosure','nativeGraphClosed','operationalBudgetClosed','executionAuthorization'):
            self.assertIs(d[key],False)

    def test_new_dependency_directive_or_extra_section_is_not_silently_ignored(self):
        p=profile();r=render_offline_v9(p);name=r['roles']['prepare']
        additions=('RuntimeDirectory=unreviewed\n','PrivateTmp=yes\n','EnvironmentFile=/tmp/x\n',
                   'LogNamespace=extra\n','ExecStartPost=/bin/true\n','[Install]\nWantedBy=multi-user.target\n')
        for text in additions:
            units=dict(r['units']);units[name]+=text
            with self.subTest(text=text),self.assertRaises(ForecastError):
                offline_dependency_inventory(p,units)

    def test_wrong_slice_extra_service_edge_or_missing_ordering_fails(self):
        p=profile();r=render_offline_v9(p);name=r['roles']['prepare'];stem='fc1'+p.identity
        for old,new in (('Requires='+stem+'-workers.slice','Requires=outside.service'),
                        ('Slice='+stem+'-workers.slice','Slice='+stem+'-root.slice'),
                        (' '+stem+'-workers.slice\nRequires=','\nRequires='),
                        ('DefaultDependencies=no','DefaultDependencies=yes')):
            units=dict(r['units']);self.assertIn(old,units[name]);units[name]=units[name].replace(old,new)
            with self.subTest(old=old),self.assertRaises(ForecastError):
                offline_dependency_inventory(p,units)

    def test_roster_duplicates_and_continuations_refused(self):
        p=profile();r=render_offline_v9(p);name=r['roles']['operator']
        for patch in ('Group=0\n','Environment=next\\\n','[Service]\n'):
            units=dict(r['units']);units[name]+=patch
            with self.subTest(patch=patch),self.assertRaises(ForecastError):
                offline_dependency_inventory(p,units)
        for units in ({}, {**r['units'],'extra.service':'[Service]\n'}):
            with self.assertRaisesRegex(ForecastError,'roster'):offline_dependency_inventory(p,units)

    def test_inventory_digest_follows_bytes_and_reaches_bootstrap_and_broker(self):
        p=profile();r=render_offline_v9(p);d=r['dependencyInventory']
        self.assertEqual(d['unitSetDigest'],r['unitSetDigest'])
        name=r['roles']['operator'];units=dict(r['units']);units[name]=units[name].replace('CPUQuota=100%','CPUQuota=50%')
        changed=offline_dependency_inventory(p,units)
        self.assertEqual(changed['explicitEdges'],d['explicitEdges'])
        self.assertNotEqual(changed['unitSetDigest'],d['unitSetDigest'])
        plan=offline_v9_plan(preparation(),p,100)
        self.assertEqual(plan['bootstrap']['graphDigest'],digest(plan['graph']))
        s=OfflineV9Integration(preparation(),p,100)
        self.assertEqual(s.receipt()['dependencyInventoryDigest'],digest(d))
        self.assertEqual(s.broker.integration_identity,s.identity)

    def test_exact_source_rules_distinguish_required_workdir_from_wanted_image(self):
        r=render_offline_v9(profile());d=r['dependencyInventory']
        self.assertEqual(len(d['mountRequests']),6)
        for row in d['mountRequests']:
            self.assertEqual(row['mountRequestKind'],'Wants' if row['directive']=='RootImage' else 'Requires')
            self.assertIsNone(row['mountUnitTargets'])
            self.assertIs(row['missingOk'],False)
        self.assertTrue(d['namespaceBindingObligations'])
        self.assertTrue(all(row['directive'] not in ('BindPaths','BindReadOnlyPaths') for row in d['mountRequests']))
        self.assertNotIn('source unavailable',' '.join(d['blockers']))
        self.assertIs(d['sourceReview']['effectiveContextVerified'],False)

    def test_synthetic_missing_ok_workdir_changes_request_kind_without_resolving_mount(self):
        p=profile();r=render_offline_v9(p);name=r['roles']['prepare']
        before=next(row for row in r['dependencyInventory']['mountRequests']
                    if row['unit']==name and row['directive']=='WorkingDirectory')
        units=dict(r['units']);units[name]=units[name].replace('WorkingDirectory=/work','WorkingDirectory=-/work')
        d=offline_dependency_inventory(p,units)
        after=next(row for row in d['mountRequests'] if row['unit']==name and row['directive']=='WorkingDirectory')
        self.assertEqual(before['mountRequestKind'],'Requires')
        self.assertEqual(after['mountRequestKind'],'Wants')
        self.assertIs(after['missingOk'],True)
        self.assertEqual(after['path'],before['path'])
        self.assertIsNone(after['mountUnitTargets'])
        self.assertIs(d['offlineClosure'],False)

    def test_declared_slice_never_becomes_observed_resolved_slice(self):
        d=render_offline_v9(profile())['dependencyInventory']
        self.assertEqual(len(d['sliceSelectionObligations']),6)
        self.assertTrue(all(row['defaultSelectionSkippedIfSliceResolved'] is True and
                            row['resolvedSliceObserved'] is False for row in d['sliceSelectionObligations']))
        self.assertIs(d['nativeGraphClosed'],False)
        self.assertIs(d['operationalBudgetClosed'],False)

    def test_unreviewed_path_expansion_is_rejected_instead_of_projected_as_literal(self):
        p=profile();r=render_offline_v9(p);name=r['roles']['prepare']
        for path in ('%t/work','/work/%n','/work/quoted"name'):
            units=dict(r['units']);units[name]=units[name].replace('WorkingDirectory=/work','WorkingDirectory='+path)
            with self.subTest(path=path),self.assertRaisesRegex(ForecastError,'unreviewed-path-syntax'):
                offline_dependency_inventory(p,units)

    def test_context_generated_module_edges_are_retained_as_conditional_activation(self):
        d=render_offline_v9(profile())['dependencyInventory']
        jobs=d['contextGeneratedJobObligations']
        self.assertEqual(len(jobs),3)
        wants=[edge['to'] for row in jobs for edge in row['edges'] if edge['kind']=='Wants']
        self.assertEqual(len(wants),9)
        self.assertEqual(set(wants),{'modprobe@loop.service','modprobe@dm_mod.service','modprobe@dm_verity.service'})
        self.assertTrue(all(row['activationPossible'] and row['activationObserved'] is False and
                            row['effectiveContextVerified'] is False for row in jobs))
        self.assertIs(d['offlineClosure'],False)
        self.assertIs(d['nativeGraphClosed'],False)

    def test_synthetic_private_devices_no_does_not_prove_device_policy_inactive(self):
        p=profile();r=render_offline_v9(p);units=dict(r['units']);name=r['roles']['prepare']
        units[name]=units[name].replace('PrivateDevices=yes','PrivateDevices=no')
        changed=offline_dependency_inventory(p,units)
        before=next(row for row in r['dependencyInventory']['contextGeneratedJobObligations'] if row['unit']==name)
        after=next(row for row in changed['contextGeneratedJobObligations'] if row['unit']==name)
        self.assertEqual(after['declaredPrivateDevices'],'no')
        self.assertEqual(before['edges'],after['edges'])
        self.assertIs(after['effectiveContextVerified'],False)

    def test_synthetic_absent_declared_image_changes_projection_without_acceptance(self):
        p=profile();r=render_offline_v9(p);units=dict(r['units']);name=r['roles']['prepare']
        units[name]='\n'.join(line for line in units[name].splitlines() if not line.startswith('RootImage='))+'\n'
        changed=offline_dependency_inventory(p,units)
        self.assertEqual(len(changed['contextGeneratedJobObligations']),2)
        self.assertFalse(any(row['unit']==name for row in changed['contextGeneratedJobObligations']))
        self.assertIs(changed['managerContextVerified'],False)
        self.assertIs(changed['offlineClosure'],False)
        self.assertNotEqual(changed['unitSetDigest'],r['unitSetDigest'])
