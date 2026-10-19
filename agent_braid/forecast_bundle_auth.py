# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded Debian Release/package and detached RSA RPM-header verification.

Optional cryptography is loaded only by the explicit audit verifier, never by
runtime imports/profile compilation. No downloads, installation or execution of
bundle artifacts. Signature validity under externally pinned publisher keys is
separate from freshness, revocation/key policy, dependency closure and admission.
"""
import base64
import hashlib
from pathlib import PurePosixPath
import struct

from .forecast_data import pin, require


def armor(raw, label):
    require(len(raw)<=2*1024**2,'pgp-armor-cap')
    start=b'-----BEGIN PGP '+label+b'-----';end=b'-----END PGP '+label+b'-----'
    normalized=raw.replace(b'\r\n',b'\n')
    require(normalized.startswith(start+b'\n') and end in normalized,'pgp-armor-boundary')
    body=normalized.split(b'\n\n',1)[1].split(end,1)[0]
    lines=body.strip().split(b'\n'); encoded=[]
    for line in lines:
        if line.startswith(b'='):continue  # CRC is not a signature authority.
        require(len(line)<=128,'pgp-armor-line')
        encoded.append(line)
    return base64.b64decode(b''.join(encoded),validate=True)


def length(raw,pos):
    require(pos<len(raw),'pgp-length')
    first=raw[pos];pos+=1
    if first<192:return first,pos
    if first<224:
        require(pos<len(raw),'pgp-length')
        return ((first-192)<<8)+raw[pos]+192,pos+1
    require(first==255 and pos+4<=len(raw),'pgp-partial-length-unsupported')
    return struct.unpack_from('>I',raw,pos)[0],pos+4


def packets(raw):
    pos=0;count=0
    while pos<len(raw):
        count+=1;require(count<=128,'pgp-packet-count')
        first=raw[pos];pos+=1;require(first&128,'pgp-packet-header')
        if first&64:
            tag=first&63;size,pos=length(raw,pos)
        else:
            tag=(first>>2)&15;kind=first&3
            require(kind<3,'pgp-indeterminate-length')
            width=(1,2,4)[kind];require(pos+width<=len(raw),'pgp-length')
            size=int.from_bytes(raw[pos:pos+width],'big');pos+=width
        require(size<=2*1024**2 and pos+size<=len(raw),'pgp-packet-range')
        yield tag,raw[pos:pos+size];pos+=size


def mpi(raw,pos):
    require(pos+2<=len(raw),'pgp-mpi')
    bits=int.from_bytes(raw[pos:pos+2],'big');size=(bits+7)//8;pos+=2
    require(0<bits<=16384 and pos+size<=len(raw),'pgp-mpi-range')
    return int.from_bytes(raw[pos:pos+size],'big'),pos+size


def rsa_keys(raw):
    result={}
    for tag,body in packets(armor(raw,b'PUBLIC KEY BLOCK')):
        if tag not in (6,14) or len(body)<6 or body[0]!=4 or body[5] not in (1,3):continue
        n,pos=mpi(body,6);e,pos=mpi(body,pos)
        require(pos==len(body) and 3072<=n.bit_length()<=16384 and e>=3 and e&1,'pgp-rsa-key')
        fingerprint=hashlib.sha1(b'\x99'+len(body).to_bytes(2,'big')+body).hexdigest().upper()
        result[fingerprint]=(n,e)
    require(result,'pgp-no-supported-keys')
    return result


def subpackets(raw):
    pos=0
    while pos<len(raw):
        size,pos=length(raw,pos)
        require(size>0 and pos+size<=len(raw),'pgp-subpacket-range')
        yield raw[pos]&127,raw[pos+1:pos+size];pos+=size


def verify_inrelease(raw, key_bytes, *, expected_key_sha256, allowed_signers):
    """Verify v4 RSA SHA256/384/512 using an already installed crypto provider.

    Caller pins the complete public-key file and exact signing fingerprints from
    its chosen external trust anchor. This does not validate OpenPGP certifications,
    expiration/revocation or accept the anchor automatically.
    """
    pin(expected_key_sha256)
    require(hashlib.sha256(key_bytes).hexdigest()==expected_key_sha256,'release-key-pin')
    require(0<len(raw)<=2*1024**2 and allowed_signers,'release-cap-or-signers')
    normalized=raw.replace(b'\r\n',b'\n')
    prefix=b'-----BEGIN PGP SIGNED MESSAGE-----\n'
    require(normalized.startswith(prefix) and b'\r' not in normalized,'release-clearsigned')
    _,separator,body=normalized.partition(b'\n\n');require(separator,'release-header')
    message,separator,signature=body.partition(b'-----BEGIN PGP SIGNATURE-----')
    require(separator and message.endswith(b'\n'),'release-signature-boundary')
    lines=message[:-1].split(b'\n')
    payload=b'\n'.join(line[2:] if line.startswith(b'- ') else line for line in lines)
    canonical=b'\r\n'.join(line.rstrip(b' \t') for line in payload.split(b'\n'))
    result=_verify_rsa(canonical,armor(b'-----BEGIN PGP SIGNATURE-----'+signature,b'SIGNATURE'),key_bytes,
                       expected_key_sha256=expected_key_sha256,allowed_signers=allowed_signers,signature_type=1)
    return payload,{'inReleaseSha256':hashlib.sha256(raw).hexdigest(),**result}


def _verify_rsa(data,signature,key_bytes,*,expected_key_sha256,allowed_signers,signature_type):
    pin(expected_key_sha256)
    require(hashlib.sha256(key_bytes).hexdigest()==expected_key_sha256,'release-key-pin')
    require(len(data)<=4*1024**2 and len(signature)<=16384 and allowed_signers,
            'release-signature-cap')
    keys={k:v for k,v in rsa_keys(key_bytes).items() if k in allowed_signers}
    require(keys,'release-no-pinned-signer')
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding,rsa
    algorithms={8:hashes.SHA256,9:hashes.SHA384,10:hashes.SHA512}
    verified=[]
    for tag,sig in packets(signature):
        if tag!=2 or len(sig)<10 or sig[:3]!=bytes((4,signature_type,1)) or sig[3] not in algorithms:continue
        hashed=int.from_bytes(sig[4:6],'big');end=6+hashed
        require(end+2<=len(sig),'release-signature-range')
        unhashed=int.from_bytes(sig[end:end+2],'big');pos=end+2+unhashed
        require(pos+2<=len(sig),'release-signature-range')
        issuer=None
        for kind,value in list(subpackets(sig[6:end]))+list(subpackets(sig[end+2:pos])):
            if kind==16:
                require(len(value)==8,'release-issuer-size');issuer=value.hex().upper()
        value,finish=mpi(sig,pos+2);require(finish==len(sig),'release-signature-tail')
        signed=data+sig[:end]+b'\x04\xff'+end.to_bytes(4,'big')
        digest=hashlib.new({8:'sha256',9:'sha384',10:'sha512'}[sig[3]],signed).digest()
        require(sig[pos:pos+2]==digest[:2],'release-digest-prefix')
        for fingerprint,(n,e) in keys.items():
            if issuer and not fingerprint.endswith(issuer):continue
            try:
                rsa.RSAPublicNumbers(e,n).public_key().verify(value.to_bytes((n.bit_length()+7)//8,'big'),
                    signed,padding.PKCS1v15(),algorithms[sig[3]]())
            except (InvalidSignature,ValueError,OverflowError):continue
            verified.append(fingerprint)
    require(verified,'release-signature-invalid-or-unsupported')
    return {'keyFileSha256':expected_key_sha256,'verifiedSigners':sorted(set(verified)),
            'signatureValid':True,'keyPolicyAccepted':False,'revocationExpiryEvaluated':False,
            'currentFreshnessAccepted':False,'executionAuthorization':False}


def verify_rpm_header(header,signature,key_bytes,*,expected_key_sha256,allowed_signers):
    """Verify RSA over exact RPM header bytes, not an unverified package payload."""
    require(len(header)>=16 and header[:4]==b'\x8e\xad\xe8\x01','rpm-header-magic')
    result=_verify_rsa(header,signature,key_bytes,expected_key_sha256=expected_key_sha256,
                       allowed_signers=allowed_signers,signature_type=0)
    return {**result,'signedHeaderSha256':hashlib.sha256(header).hexdigest(),
            'scope':'Immutable RPM header only; payload/file bindings require separate verification',
            'payloadBindingAccepted':False,'sourceAuthenticityAccepted':False}


def release_index(payload,path):
    """Bind one exact index to SHA256/size in authenticated Release payload."""
    active=False;rows=[]
    for line in payload.splitlines():
        if not line.startswith(b' '):active=line==b'SHA256:';continue
        if not active:continue
        parts=line.split()
        require(len(parts)==3,'release-index-row')
        if parts[2].decode()==path:
            value=parts[0].decode();pin(value)
            size=int(parts[1]);require(0<size<=32*1024**2,'release-index-size')
            rows.append({'path':path,'sha256':value,'bytes':size})
    require(len(rows)==1,'release-index-missing-or-duplicate')
    return rows[0]


def package_stanza(index, *, name,version,architecture='arm64'):
    require(len(index)<=128*1024**2,'packages-index-cap')
    matches=[]
    for block in index.split(b'\n\n'):
        if not block.startswith(b'Package: '+name.encode()+b'\n'):continue
        row={};last=None
        for line in block.splitlines():
            if line.startswith(b' ') and last:
                row[last]+=' '+line.strip().decode();continue
            key,separator,value=line.partition(b':')
            require(separator,'packages-field')
            last=key.decode();require(last not in row,'packages-duplicate-field')
            row[last]=value.strip().decode()
        if row.get('Version')==version and row.get('Architecture')==architecture:matches.append(row)
    require(len(matches)==1,'packages-identity-missing-or-duplicate')
    row=matches[0];pin(row['SHA256']);size=int(row['Size'])
    path=PurePosixPath(row['Filename'])
    require(not path.is_absolute() and '..' not in path.parts and 0<size<=16*1024**2,'packages-artifact-range')
    return row


def verify_deb(raw,stanza):
    require(len(raw)==int(stanza['Size']) and hashlib.sha256(raw).hexdigest()==stanza['SHA256'],
            'packages-deb-hash-or-size')
    return {'package':stanza['Package'],'version':stanza['Version'],'architecture':stanza['Architecture'],
            'sha256':stanza['SHA256'],'bytes':len(raw),'indexBindingVerified':True,
            'dependencyClosureAccepted':False,'executionAuthorization':False}
