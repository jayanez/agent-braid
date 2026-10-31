# SPDX-License-Identifier: AGPL-3.0-only
"""New staged-file census regressions only; no model or native admission control."""
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest

from agent_braid.forecast_build import dependency_build_policy
from agent_braid.forecast_data import canonical, ForecastError
from agent_braid.forecast_host_census import ROLES, ELF_ROLES, inspect_staged_host


def elf(bpf=False):
    raw=bytearray(64);raw[:7]=b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI',raw,16,1 if bpf else 2,247 if bpf else 183,1)
    return bytes(raw)


class HostCensusTests(unittest.TestCase):
    def stage(self,root):
        policy=dependency_build_policy();payloads={}
        for role in ROLES:
            if role in ELF_ROLES: value=elf()
            elif role=='execCensus':value=elf(True)
            elif role=='kernelConfig':
                value=''.join('# '+k+' is not set\n' if v=='n' else k+'='+v+'\n'
                    for k,v in policy['kernel']['config'].items()).encode()
            elif role.endswith('Config'):
                value=''.join('/* #undef '+k+' */\n' if v is None else '#define '+k+' '+v+'\n'
                    for k,v in policy['components'][role[:-6]]['macros'].items()).encode()
            else:value=b'# private operator source\n'
            payloads[role]=value
        m={'version':'fc1-staged-host-v1','sourceDigest':'a'*64,'provenanceSha256':'b'*64,
           'ownerUid':os.getuid(),'files':[],'directories':[], 'bindings':{r:r for r in ROLES},
           'forbiddenElfSha256':[hashlib.sha256(elf()+b'udev-code').hexdigest()]}
        for name,raw in payloads.items():
            (root/name).write_bytes(raw);mode=0o755 if name in ELF_ROLES else 0o644
            (root/name).chmod(mode)
            m['files'].append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'mode':mode})
        return m

    def inspect(self,root,m):
        raw=canonical(m)
        return inspect_staged_host(root,raw,expected_manifest_sha256=hashlib.sha256(raw).hexdigest())

    def test_closed_staging_read_is_not_a_boot_or_provenance_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();report=self.inspect(root,self.stage(root))
        self.assertTrue(report['closedStagingInventory']);self.assertEqual(report['files'],len(ROLES))
        for key in ('sourceObjectCorrespondenceVerified','immutableFutureBytesVerified',
                    'runningHostVerified','hostActivationClosed','nativeQualification','executionAuthorization'):
            self.assertFalse(report[key])

    def test_unlisted_hidden_file_and_missing_declared_file_refuse(self):
        for extra in (True,False):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory).resolve();m=self.stage(root)
                if extra:(root/'.unexpected').write_bytes(b'x')
                else:(root/'git').unlink()
                with self.subTest(extra=extra),self.assertRaises(ForecastError):self.inspect(root,m)

    def test_symlink_and_hardlink_never_follow_or_hide_a_copy(self):
        for symbolic in (True,False):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory).resolve();m=self.stage(root)
                if symbolic:(root/'alias').symlink_to(root/'git')
                else:os.link(root/'git',root/'alias')
                with self.subTest(symbolic=symbolic),self.assertRaisesRegex(ForecastError,'alias-or-special'):
                    self.inspect(root,m)

    def test_renamed_forbidden_elf_is_rejected_even_without_execute_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();m=self.stage(root);raw=elf()+b'udev-code'
            (root/'renamed-data').write_bytes(raw);(root/'renamed-data').chmod(0o644)
            m['files'].append({'path':'renamed-data','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'mode':0o644})
            with self.assertRaisesRegex(ForecastError,'forbidden-copy'):self.inspect(root,m)

    def test_host_udev_alias_path_and_input_pin_cannot_be_overridden(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();m=self.stage(root);m['directories']=['etc/udev']
            with self.assertRaisesRegex(ForecastError,'udev-path'):self.inspect(root,m)
            raw=canonical(self.stage(root))
            with self.assertRaisesRegex(ForecastError,'manifest-pin'):
                inspect_staged_host(root,raw,expected_manifest_sha256='0'*64)

    def test_regular_open_is_nonblocking_and_no_controlling_terminal(self):
        # New race-hardening assertion, not a rerun of the five earlier cases.
        from unittest.mock import patch
        actual=os.open;regular_flags=[]
        def checked(path,flags,*args,**kwargs):
            if not flags & os.O_DIRECTORY:regular_flags.append(flags)
            return actual(path,flags,*args,**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();m=self.stage(root)
            with patch('agent_braid.forecast_host_census.os.open',side_effect=checked):self.inspect(root,m)
        self.assertEqual(len(regular_flags),len(ROLES))
        self.assertTrue(all(flags&os.O_NONBLOCK and flags&os.O_NOCTTY for flags in regular_flags))
