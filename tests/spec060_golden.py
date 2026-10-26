# SPDX-License-Identifier: AGPL-3.0-only
"""Golden-byte helpers for SPEC-060.

The fixtures under ``tests/fixtures/spec060`` were captured from the develop
commit that preceded any SPEC-060 behaviour change (portable server v0.1,
plugin alpha.4). Run, artifact and path-dependent identifiers are replaced by
placeholders before comparing; every other byte must match.
"""
from __future__ import annotations

from pathlib import Path
import re

from agent_braid import __version__

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "spec060"
GOLDEN_CANDIDATE_VERSION = "0.1.0a1"


def golden(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def normalize(text: str) -> str:
    text = re.sub(r"ev-[0-9a-f]{32}", "ev-ID", text)
    text = re.sub(r"/runs/[0-9a-f]{32}/", "/runs/RUN/", text)
    text = re.sub(r'"sourceIdentity":"sha256:[0-9a-f]{64}"', '"sourceIdentity":"sha256:SRC"', text)
    return text.replace(f'"candidateVersion":"{__version__}"', f'"candidateVersion":"{GOLDEN_CANDIDATE_VERSION}"')
