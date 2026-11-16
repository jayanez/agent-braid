# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-003 (T004): typed redaction of trace content and the post-redaction scan.

The credential patterns here are the single source shared with the SPEC-069 native-run driver
(`lightning_hosts.SECRET_PATTERNS`). A redacted text is accepted only when a post-scan finds no
literal secret, pattern, email or home path; otherwise it is refused with `redaction-incomplete`.
Encoded forms (URL-encoded, JSON \\u escapes, base64) are decoded for the scan and replaced by
`[REDACTED:encoded]` when they hide a hit; a value split across JSON fields is caught by scanning the
joined fields and refused (SPEC-074 REQ-004, T005). Emails become `[REDACTED:email:<8-hex>]`, a hash salted per run (OD-2), so tags cannot be linked
across runs. Standard library only; no I/O.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
from typing import Any

REFUSAL = 'redaction-incomplete'
SALT_BYTES = 16

PRIVATE_KEY = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.*?-----END [A-Z ]*PRIVATE KEY-----)?', re.S)
BEARER = re.compile(r'(?i)\b(?:bearer|token)\s+[A-Za-z0-9._~+/\-]{16,}=*')
TOKENS = [re.compile(p) for p in (
    r'\bsk-ant-[A-Za-z0-9_\-]{8,}', r'\bsk-[A-Za-z0-9_\-]{16,}', r'\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}',
    r'\bAIza[0-9A-Za-z_\-]{20,}', r'\bxox[abprs]-[A-Za-z0-9\-]{10,}', r'\bAKIA[0-9A-Z]{16}\b',
    r'\bya29\.[0-9A-Za-z_\-]{20,}')]
B64_RUN = re.compile(r'[A-Za-z0-9+/_\-]{16,}={0,2}')
ESCAPED = re.compile(r'\\u([0-9a-fA-F]{4})')
WORD = re.compile(r'[^\s"\'<>,;]+')
EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}')

# The SPEC-069 scan set: token shapes, the bearer header and the private-key header line.
SECRET_PATTERNS = [*TOKENS[:5], re.compile(r'(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}'),
                   re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'), TOKENS[5]]


class RedactionError(ValueError):
    def __init__(self, message: str, code: str = REFUSAL):
        super().__init__(message)
        self.code = code


def new_salt() -> bytes:
    return os.urandom(SALT_BYTES)


class Redactor:
    """Redacts with known literal secrets, the shared patterns, a per-run email salt and the owner's home path."""

    def __init__(self, salt: bytes, *, secrets: list[str] | tuple[str, ...] = (), home: str | Path | None = None):
        if not isinstance(salt, bytes) or len(salt) < SALT_BYTES:
            raise RedactionError('The email salt must be at least 16 random bytes')
        self._salt = salt
        self._secrets = sorted({s for s in secrets if s and len(s) >= 6}, key=len, reverse=True)
        home = str(Path.home() if home is None else home).rstrip('/')
        self._home = home if len(home) > 1 else None

    def _email(self, match: re.Match) -> str:
        tag = hmac.new(self._salt, match.group(0).lower().encode(), hashlib.sha256).hexdigest()[:8]
        return f'[REDACTED:email:{tag}]'

    def redact(self, text: str) -> str:
        text = PRIVATE_KEY.sub('[REDACTED:private-key]', text)
        for value in self._secrets:
            text = text.replace(value, '[REDACTED:secret]')
        text = BEARER.sub('[REDACTED:bearer]', text)
        for pattern in TOKENS:
            text = pattern.sub('[REDACTED:token]', text)
        text = EMAIL.sub(self._email, text)
        if self._home:
            text = re.sub(re.escape(self._home) + r'(?![A-Za-z0-9._\-])', '~', text)
        return self._redact_encoded(text)

    def _redact_encoded(self, text: str) -> str:
        def b64(match: re.Match) -> str:
            return '[REDACTED:encoded]' if self._scan_plain(_b64(match.group(0))) else match.group(0)

        def word(match: re.Match) -> str:
            value = match.group(0)
            if ('%' in value or '\\u' in value) and self._scan_plain(_unescape(unquote(value))):
                return '[REDACTED:encoded]'
            return value
        return WORD.sub(word, B64_RUN.sub(b64, text))

    def scan(self, text: str) -> list[str]:
        """Classes still present in the text or any decoded view of it; empty means clean. Never returns the match."""
        views = [text, unquote(text), _unescape(text)] + [_b64(m.group(0)) for m in B64_RUN.finditer(text)]
        found: list[str] = []
        for view in views:
            found += [cls for cls in self._scan_plain(view) if cls not in found]
        return found

    def _scan_plain(self, text: str) -> list[str]:
        found = ['secret'] if any(s in text for s in self._secrets) else []
        found += ['private-key'] if PRIVATE_KEY.search(text) else []
        found += ['bearer'] if BEARER.search(text) else []
        found += ['token'] if any(p.search(text) for p in TOKENS) else []
        found += ['email'] if EMAIL.search(text) else []
        found += ['home'] if self._home and self._home in text else []
        return found

    def clean_text(self, text: str) -> str:
        redacted = self.redact(text)
        found = self.scan(redacted)
        if found:
            raise RedactionError(f"Post-redaction scan found: {', '.join(found)}")
        return redacted

    def clean(self, value: Any) -> Any:
        """Redact every string (keys included) of a JSON value, then scan its serialized form.

        A hit that spans two fields of the input cannot be redacted field by field, so it is refused.
        """
        if self._spans_fields(_leaves(value)):
            raise RedactionError('A sensitive value is split across fields')
        redacted = self._walk(value)
        found = self.scan(json.dumps(redacted, ensure_ascii=False))
        found += [cls for cls in self.scan(''.join(_leaves(redacted))) if cls not in found]
        if found:
            raise RedactionError(f"Post-redaction scan found: {', '.join(found)}")
        return redacted

    def _spans_fields(self, leaves: list[str]) -> bool:
        ends, offset = [], 0
        for leaf in leaves:
            offset += len(leaf)
            ends.append(offset)
        joined = ''.join(leaves)
        patterns = [PRIVATE_KEY, BEARER, *TOKENS, EMAIL] + [re.compile(re.escape(v)) for v in self._secrets]
        patterns += [re.compile(re.escape(self._home))] if self._home else []
        for pattern in patterns:
            for match in pattern.finditer(joined):
                cut = next((end for end in ends if match.start() < end < match.end()), None)
                # A field that already holds a recognizable prefix is redacted on its own; only a hidden split is refused.
                if cut is not None and not pattern.fullmatch(joined, match.start(), cut):
                    return True
        return False

    def _walk(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, list):
            return [self._walk(item) for item in value]
        if isinstance(value, dict):
            return {self.redact(key): self._walk(item) for key, item in value.items()}
        return value


def _leaves(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _leaves(item)]
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _leaves(item)]  # values only: keys are scanned in json
    return []


def unquote(text: str) -> str:
    """Percent-decoding (UTF-8), kept local: the BL.0 boundary forbids importing urllib."""
    return re.sub(r'(?:%[0-9A-Fa-f]{2})+',
                  lambda m: bytes.fromhex(m.group(0).replace('%', '')).decode('utf-8', 'replace'), text)


def _unescape(text: str) -> str:
    return ESCAPED.sub(lambda m: chr(int(m.group(1), 16)), text)


def _b64(run: str) -> str:
    try:
        raw = base64.b64decode(run.replace('-', '+').replace('_', '/') + '=' * (-len(run) % 4), validate=False)
    except (binascii.Error, ValueError):
        return ''
    return raw.decode('utf-8', 'ignore')
