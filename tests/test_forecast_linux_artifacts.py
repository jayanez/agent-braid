# SPDX-License-Identifier: AGPL-3.0-only
"""Tiny parser fixtures only; never inspect actual Linux artifacts or execute them."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from agent_braid.forecast_linux_artifacts import inspect_bundle,elf_header,REQUIRED
from agent_braid.forecast_data import ForecastError


def elf(machine=183,typ=3):
    raw=bytearray(64);raw[:7]=b'\x7fELF\x02\x01\x01';struct.pack_into('<HHI',raw,16,typ,machine,1)
    return bytes(raw)


class ArtifactTests(unittest.TestCase):
    def make(self,root):
        rows=[];bindings={}
        for role in sorted(REQUIRED):
            raw=elf(247,1) if role=='censusObject' else elf()
            (root/role).write_bytes(raw)
            rows.append(dict(path=role,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                             kind='bpf-elf' if role=='censusObject' else 'elf'))
            bindings[role]=role
        return dict(version='fc1-linux-artifacts-v1',architecture='aarch64',files=rows,
                    bindings=bindings,provenanceSha256='a'*64)

    def inspect(self,root,manifest):
        raw=json.dumps(manifest).encode()
        return inspect_bundle(root,raw,expected_manifest_sha256=hashlib.sha256(raw).hexdigest())

    def test_hash_and_elf_readback_never_claim_authenticity_or_native_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();manifest=self.make(root)
            result=self.inspect(root,manifest)
            self.assertEqual(result['files'],len(REQUIRED))
            self.assertFalse(result['sourceAuthenticityAccepted'])
            self.assertFalse(result['dependencyClosureAccepted'])
            self.assertFalse(result['executionAuthorization'])
            (root/'git').write_bytes(b'x'*64)
            with self.assertRaisesRegex(ForecastError,'artifact-hash'): self.inspect(root,manifest)

    def test_wrong_architecture_self_attestation_and_escape_refuse(self):
        with self.assertRaisesRegex(ForecastError,'architecture'): elf_header(elf(62))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();manifest=self.make(root)
            manifest['signatureVerified']=True
            with self.assertRaisesRegex(ForecastError,'manifest-fields'): self.inspect(root,manifest)
            del manifest['signatureVerified'];manifest['files'][0]['path']='../outside'
            with self.assertRaisesRegex(ForecastError,'artifact-path'): self.inspect(root,manifest)

    def test_symlink_input_and_unpinned_manifest_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();manifest=self.make(root)
            (root/'git').unlink();(root/'git').symlink_to('python')
            with self.assertRaises(OSError): self.inspect(root,manifest)
            with self.assertRaisesRegex(ForecastError,'manifest-pin'):
                inspect_bundle(root,b'{}',expected_manifest_sha256='b'*64)

class ElfDependencyTests(unittest.TestCase):
    def versioned_image(self):
        raw=self.image();strings=b'\0libc.so.6\0GLIBC_2.17\0'
        raw[0x200:0x200+len(strings)]=strings
        struct.pack_into('<Q',raw,176+32,128)
        for i,pair in enumerate(((5,0x1200),(10,len(strings)),(1,1),
                (0x6ffffffe,0x1280),(0x6fffffff,1),(0x6ffffffc,0x12c0),(0x6ffffffd,1),(0,0))):
            struct.pack_into('<qQ',raw,0x180+16*i,*pair)
        struct.pack_into('<HHIII',raw,0x280,1,1,1,16,0)
        struct.pack_into('<IHHII',raw,0x290,0,0,2,strings.index(b'GLIBC'),0)
        struct.pack_into('<HHHHIII',raw,0x2c0,1,0,2,1,0,20,0)
        struct.pack_into('<II',raw,0x2d4,strings.index(b'GLIBC'),0)
        return raw

    def test_required_and_provided_versions_do_not_imply_loader_acceptance(self):
        from agent_braid.forecast_linux_artifacts import elf_dependencies
        value=elf_dependencies(self.versioned_image())
        self.assertEqual(value['requiredVersions'],{'libc.so.6':['GLIBC_2.17']})
        self.assertEqual(value['providedVersions'],['GLIBC_2.17'])
        self.assertFalse(value['loaderResolutionVerified'])

    def test_version_tables_reject_bad_mapping_counts_chains_and_strings(self):
        from agent_braid.forecast_linux_artifacts import elf_dependencies
        changes=[(0x180+3*16+8,'<Q',0x1fff),(0x180+4*16+8,'<Q',129),
                 (0x280,'<H',2),(0x290+12,'<I',16),(0x2c0+6,'<H',0),(0x290+8,'<I',999)]
        for offset,fmt,value in changes:
            raw=self.versioned_image();struct.pack_into(fmt,raw,offset,value)
            with self.subTest(offset=offset),self.assertRaises(ForecastError):elf_dependencies(raw)

    def image(self):
        raw=bytearray(768);raw[:64]=elf()
        struct.pack_into('<Q',raw,32,64);struct.pack_into('<HH',raw,54,56,3)
        struct.pack_into('<IIQQQQQQ',raw,64,1,0,0,0x1000,0,768,768,4096)
        interpreter=b'/lib/ld-linux-aarch64.so.1\0'
        struct.pack_into('<IIQQQQQQ',raw,120,3,0,0x150,0,0,len(interpreter),len(interpreter),1)
        struct.pack_into('<IIQQQQQQ',raw,176,2,0,0x180,0,0,64,64,8)
        raw[0x150:0x150+len(interpreter)]=interpreter
        strings=b'\0libc.so.6\0';raw[0x200:0x200+len(strings)]=strings
        for i,pair in enumerate(((5,0x1200),(10,len(strings)),(1,1),(0,0))):
            struct.pack_into('<qQ',raw,0x180+16*i,*pair)
        return raw

    def test_interpreter_and_needed_are_data_not_loader_resolution(self):
        from agent_braid.forecast_linux_artifacts import elf_dependencies
        value=elf_dependencies(self.image())
        self.assertEqual(value['needed'],['libc.so.6'])
        self.assertEqual(value['interpreter'],'/lib/ld-linux-aarch64.so.1')
        self.assertFalse(value['loaderResolutionVerified'])

    def test_program_header_and_string_ranges_are_bounded(self):
        from agent_braid.forecast_linux_artifacts import elf_dependencies
        raw=self.image();struct.pack_into('<H',raw,56,129)
        with self.assertRaisesRegex(ForecastError,'program-headers'):elf_dependencies(raw)
        raw=self.image();struct.pack_into('<Q',raw,0x180+16+8,2**30)
        with self.assertRaisesRegex(ForecastError,'string-table'):elf_dependencies(raw)
