# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded metadata parser controls; no artifact execution or key acceptance."""
import base64
import hashlib
import unittest
from agent_braid import forecast_bundle_auth as auth
from agent_braid.forecast_data import ForecastError


class BundleAuthTests(unittest.TestCase):
    def test_packets_reject_truncation_partial_indeterminate_and_excess_count(self):
        for raw in (b'\xc2\xe0',b'\x8b',b'\xc2\x05x',b'\xc2\x00'*129):
            with self.subTest(raw=raw[:6]),self.assertRaises(ForecastError):list(auth.packets(raw))
        self.assertEqual(list(auth.packets(b'\xc2\x01x')),[(2,b'x')])

    def test_armor_decodes_data_without_treating_crc_as_authority(self):
        raw=b'-----BEGIN PGP SIGNATURE-----\n\n'+base64.b64encode(b'abc')+b'\n=ignored\n-----END PGP SIGNATURE-----\n'
        self.assertEqual(auth.armor(raw,b'SIGNATURE'),b'abc')

    def test_external_key_pin_precedes_crypto_provider_loading(self):
        with self.assertRaisesRegex(ForecastError,'key-pin'):
            auth.verify_inrelease(b'bad',b'key',expected_key_sha256='a'*64,allowed_signers=['b'*40])

    def test_rpm_header_signature_scope_rejects_bad_magic_pin_and_oversize(self):
        key=b'key';keysha=hashlib.sha256(key).hexdigest();header=b'\x8e\xad\xe8\x01'+b'\0'*12
        with self.assertRaisesRegex(ForecastError,'rpm-header-magic'):
            auth.verify_rpm_header(b'not a header',b'',key,expected_key_sha256=keysha,allowed_signers=['b'*40])
        with self.assertRaisesRegex(ForecastError,'key-pin'):
            auth.verify_rpm_header(header,b'',key,expected_key_sha256='a'*64,allowed_signers=['b'*40])
        with self.assertRaisesRegex(ForecastError,'signature-cap'):
            auth.verify_rpm_header(header,b'x'*16385,key,expected_key_sha256=keysha,allowed_signers=['b'*40])

    def test_release_requires_unique_exact_index_and_bounded_size(self):
        row=b' '+b'a'*64+b' 20 main/binary-arm64/Packages.xz\n'
        payload=b'SHA256:\n'+row
        self.assertEqual(auth.release_index(payload,'main/binary-arm64/Packages.xz')['bytes'],20)
        for raw in (payload+row,payload.replace(b' 20 ',b' 999999999 '),b'SHA1:\n'+row):
            with self.assertRaises(ForecastError):auth.release_index(raw,'main/binary-arm64/Packages.xz')

    def test_exact_package_identity_hash_size_and_path(self):
        blob=b'archive bytes';digest=hashlib.sha256(blob).hexdigest()
        index=f'Package: p\nVersion: 1\nArchitecture: arm64\nFilename: pool/p.deb\nSize: {len(blob)}\nSHA256: {digest}\n'.encode()
        row=auth.package_stanza(index,name='p',version='1')
        result=auth.verify_deb(blob,row)
        self.assertTrue(result['indexBindingVerified']);self.assertFalse(result['executionAuthorization'])
        with self.assertRaisesRegex(ForecastError,'hash-or-size'):auth.verify_deb(blob+b'x',row)
        for raw in (index.replace(b'pool/p.deb',b'../p.deb'),index.replace(b'arm64',b'amd64'),
                    index+b'\n'+index,index+b'Version: 1\n'):
            with self.assertRaises((ForecastError,KeyError)):auth.package_stanza(raw,name='p',version='1')


if __name__=='__main__':unittest.main()
