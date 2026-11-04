# SPDX-License-Identifier: AGPL-3.0-only
"""Where the first-party web bundle and its vendored files live (SPEC-061 T047): derived once, no network code."""
from __future__ import annotations

from pathlib import Path

WEB_SOURCE_DIR = Path(__file__).resolve().parent.parent / "integrations" / "agent-braid-view" / "web"
WEB_PACKAGE_DIR = Path(__file__).resolve().parent / "view_assets" / "web"  # written by build_support.py (T043)
VENDOR_DIRNAME = "vendor"


def vendor_dir_of(bundle_dir: Path) -> Path:
    """The vendored-code directory of a web bundle directory."""
    return bundle_dir / VENDOR_DIRNAME


__all__ = ["VENDOR_DIRNAME", "WEB_PACKAGE_DIR", "WEB_SOURCE_DIR", "vendor_dir_of"]
