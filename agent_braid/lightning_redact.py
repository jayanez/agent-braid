# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-003 (T004): typed redaction of trace content and the post-redaction scan.

The credential patterns here are the single source shared with the SPEC-069 native-run driver
(`lightning_hosts.SECRET_PATTERNS`). A redacted text is accepted only when a post-scan finds no
literal secret, pattern, email or home path; otherwise it is refused with `redaction-incomplete`.
Emails become `[REDACTED:email:<8-hex>]`, a hash salted per run (OD-2), so tags cannot be linked
across runs. Standard library only; no I/O.
"""
from __future__ import annotations

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
        return text

    def scan(self, text: str) -> list[str]:
        """Classes still present; empty means clean. Never returns the matched text."""
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
        """Redact every string (keys included) of a JSON value, then scan its serialized form."""
        redacted = self._walk(value)
        found = self.scan(json.dumps(redacted, ensure_ascii=False))
        if found:
            raise RedactionError(f"Post-redaction scan found: {', '.join(found)}")
        return redacted

    def _walk(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, list):
            return [self._walk(item) for item in value]
        if isinstance(value, dict):
            return {self.redact(key): self._walk(item) for key, item in value.items()}
        return value
