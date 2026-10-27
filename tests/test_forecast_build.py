# SPDX-License-Identifier: AGPL-3.0-only
"""Contract boundaries only; no build, download or real-source processing."""
from copy import deepcopy
import unittest
from agent_braid.forecast_build import (ROLES,build_recipe,compare_outputs,
                                        build_recipe_v2,dependency_build_policy,inspect_dependency_config,
                                        inspect_kernel_helper_config)
from agent_braid.forecast_data import ForecastError,digest


class BuildTests(unittest.TestCase):
    def recipe(self):
        return build_recipe({role:{'sha256':'a'*64,'bytes':1,'provenanceSha256':'b'*64}
                             for role in ROLES},source_digest='c'*64,
                            dependency_manifest_sha256='d'*64)

    def reports(self):
        recipe=self.recipe()
        reports=[{'recipeDigest':digest(recipe),'buildId':key*64,
                  'files':{'usr/bin/git':{'sha256':'e'*64,'bytes':1}}} for key in ('1','2')]
        return recipe,reports

    def test_missing_tool_or_mutable_pin_refuses_recipe(self):
        rows=self.recipe()['artifacts'];del rows['clang-bpf']
        with self.assertRaisesRegex(ForecastError,'role-roster'):
            build_recipe(rows,source_digest='c'*64,dependency_manifest_sha256='d'*64)
        rows=self.recipe()['artifacts'];rows['clang-bpf']['sha256']='latest'
        with self.assertRaises(ForecastError):
            build_recipe(rows,source_digest='c'*64,dependency_manifest_sha256='d'*64)

    def test_budget_is_two_builds_and_inspection_without_authority(self):
        recipe=self.recipe();self.assertEqual(recipe['totalSeconds'],18000)
        self.assertFalse(recipe['buildExecutionAuthorized']);self.assertFalse(recipe['networkDuringBuild'])

    def test_equal_declarations_do_not_accept_reproducibility(self):
        recipe,reports=self.reports();result=compare_outputs(recipe,*reports)
        self.assertTrue(result['declaredOutputsMatch']);self.assertFalse(result['reproducibilityAccepted'])

    def test_difference_including_missing_file_is_retained(self):
        recipe,reports=self.reports();reports[1]['files']['usr/bin/extra']={'sha256':'f'*64,'bytes':1}
        self.assertEqual(compare_outputs(recipe,*reports)['differences'],['usr/bin/extra'])

    def test_replayed_build_changed_recipe_and_path_escape_are_refused(self):
        recipe,reports=self.reports()
        for edit in ('same','recipe','path'):
            changed=deepcopy(reports)
            if edit=='same':changed[1]['buildId']=changed[0]['buildId']
            if edit=='recipe':changed[1]['recipeDigest']='f'*64
            if edit=='path':changed[1]['files']['../escape']={'sha256':'f'*64,'bytes':1}
            with self.subTest(edit=edit),self.assertRaises(ForecastError):compare_outputs(recipe,*changed)


class DependencyConfigTests(unittest.TestCase):
    def header(self,component):
        macros=dependency_build_policy()['components'][component]['macros']
        return ''.join(('/* #undef '+k+' */\n') if v is None else
                       '#define '+k+' '+v+'\n' for k,v in macros.items()).encode()

    def test_literal_headers_never_accept_compiler_or_host(self):
        for component in ('cryptsetup','libdevmapper'):
            result=inspect_dependency_config(component,self.header(component))
            self.assertTrue(result['literalConstraintsSatisfied'])
            for key in ('compiledHeaderUseVerified','cryptoBackendSourceVerified',
                        'dependencyClosureAccepted','executionAuthorization'):
                self.assertFalse(result[key])

    def test_zero_define_does_not_disable_ifdef_filemapd(self):
        raw=self.header('libdevmapper').replace(b'/* #undef DMFILEMAPD */',b'#define DMFILEMAPD 0')
        with self.assertRaisesRegex(ForecastError,'unsafe:DMFILEMAPD'):
            inspect_dependency_config('libdevmapper',raw)

    def test_missing_duplicate_conditional_and_indirect_macros_refuse(self):
        raw=self.header('libdevmapper')
        for bad in (raw.split(b'\n',1)[1],raw+b'#undef DMFILEMAPD\n',
                    b'#if 0\n'+raw+b'#endif\n',raw+b'#include "other.h"\n',
                    b'#define OTHER \\\n'+raw):
            with self.subTest(raw=bad),self.assertRaises(ForecastError):
                inspect_dependency_config('libdevmapper',bad)

    def test_enabled_token_udev_and_argon2_are_rejected(self):
        raw=self.header('cryptsetup')
        for before,after in ((b'/* #undef USE_UDEV */',b'#define USE_UDEV 1'),
                             (b'/* #undef USE_EXTERNAL_TOKENS */',b'#define USE_EXTERNAL_TOKENS 1'),
                             (b'#define USE_INTERNAL_ARGON2 0',b'#define USE_INTERNAL_ARGON2 1')):
            with self.subTest(macro=after),self.assertRaises(ForecastError):
                inspect_dependency_config('cryptsetup',raw.replace(before,after))

    def test_comment_line_splice_cannot_hide_required_macro(self):
        raw=self.header('cryptsetup')
        for newline in (b'\n',b'\r\n'):
            bad=raw.replace(b'#define ENABLE_AF_ALG 1',
                            b'// hidden by C line splicing \\'+newline+b'#define ENABLE_AF_ALG 1')
            with self.subTest(newline=newline),self.assertRaisesRegex(ForecastError,'indirection'):
                inspect_dependency_config('cryptsetup',bad)

    def test_policy_copy_never_mutates_pins_or_accepts_source_as_binary(self):
        a=dependency_build_policy();a['components']['cryptsetup']['commit']='changed'
        b=dependency_build_policy()
        self.assertNotEqual(a['components']['cryptsetup']['commit'],b['components']['cryptsetup']['commit'])
        self.assertFalse(b['sourceBuildCorrespondenceVerified']);self.assertFalse(b['hostActivationClosed'])

    def inputs(self):
        rows={r:{'sha256':'a'*64,'bytes':1,'provenanceSha256':'b'*64} for r in ROLES}
        for role,component in (('cryptsetup','cryptsetup'),('libdevmapper-source','libdevmapper')):
            dep=dependency_build_policy()['components'][component]
            rows[role]={'sha256':dep['sourceArchiveSha256'],'bytes':dep['sourceArchiveBytes'],
                        'provenanceSha256':'b'*64}
        return rows

    def test_v2_binds_sources_without_increasing_build_envelope(self):
        recipe=build_recipe_v2(self.inputs(),source_digest='c'*64,dependency_manifest_sha256='d'*64)
        self.assertEqual(recipe['version'],'fc1-linux-build-recipe-v2')
        self.assertEqual(recipe['totalSeconds'],18000);self.assertEqual(recipe['diskBytes'],20*1024**3)
        self.assertEqual(recipe['dependencyPolicyDigest'],digest(recipe['dependencyPolicy']))
        self.assertFalse(recipe['dependencyClosureAccepted']);self.assertFalse(recipe['buildExecutionAuthorized'])
        reports=[{'recipeDigest':digest(recipe),'buildId':key*64,
                  'files':{'lib/libcryptsetup.so':{'sha256':'e'*64,'bytes':1}}} for key in ('1','2')]
        self.assertFalse(compare_outputs(recipe,*reports)['reproducibilityAccepted'])
        recipe['dependencyPolicy']['components']['cryptsetup']['configure'].remove('--disable-external-tokens')
        with self.assertRaisesRegex(ForecastError,'recipe-drift'):compare_outputs(recipe,*reports)

    def test_v2_cannot_substitute_package_or_mutable_tag_for_source(self):
        rows=self.inputs();rows['libdevmapper-source']['sha256']='a'*64
        with self.assertRaisesRegex(ForecastError,'dependency-source'):
            build_recipe_v2(rows,source_digest='c'*64,dependency_manifest_sha256='d'*64)
        rows=self.inputs();rows['libdevmapper-source']['bytes']=float(rows['libdevmapper-source']['bytes'])
        with self.assertRaises(ForecastError):
            build_recipe_v2(rows,source_digest='c'*64,dependency_manifest_sha256='d'*64)

    def kernel_config(self):
        return ''.join('# '+k+' is not set\n' if v=='n' else k+'='+v+'\n'
                       for k,v in dependency_build_policy()['kernel']['config'].items()).encode()

    def test_kernel_helpers_disabled_in_config_does_not_attest_live_host(self):
        result=inspect_kernel_helper_config(self.kernel_config())
        self.assertTrue(result['literalConstraintsSatisfied'])
        for key in ('emittedKernelCorrespondenceVerified','bootedKernelVerified',
                    'udevAbsenceVerified','nativeQualification','executionAuthorization'):
            self.assertFalse(result[key])

    def test_kernel_modules_helper_path_and_nonbuiltin_features_refuse(self):
        raw=self.kernel_config()
        for before,after in ((b'# CONFIG_MODULES is not set',b'CONFIG_MODULES=y'),
                             (b'CONFIG_STATIC_USERMODEHELPER_PATH=""',b'CONFIG_STATIC_USERMODEHELPER_PATH="/sbin/helper"'),
                             (b'CONFIG_DM_VERITY=y',b'CONFIG_DM_VERITY=m')):
            with self.subTest(line=after),self.assertRaises(ForecastError):
                inspect_kernel_helper_config(raw.replace(before,after))
        for bad in (raw.split(b'\n',1)[1],raw+b'CONFIG_MODULES=n\n'):
            with self.assertRaises(ForecastError):inspect_kernel_helper_config(bad)
