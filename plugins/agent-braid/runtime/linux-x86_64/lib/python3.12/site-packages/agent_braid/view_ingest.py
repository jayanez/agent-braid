# SPDX-License-Identifier: AGPL-3.0-only
"""What an ingest handler may say to the viewer server, without any network code (SPEC-061 T047).

`IngestRefusal` and the dropped-names inventory limits are shared by the server (`view_serve`, which owns
the sockets) and the hook ingest (`view_hooks`). They live here so that loading a handler does not load the
network modules.
"""
from __future__ import annotations

INGEST_STATUSES = (400, 403, 503)
MAX_INVENTORY_NAMES = 256
MAX_INVENTORY_NAME_LENGTH = 64


class IngestRefusal(Exception):
    """An ingest handler refuses its input; the server answers `status` and stores nothing."""

    def __init__(self, status: int) -> None:
        if status not in INGEST_STATUSES:
            raise ValueError(f"an ingest refusal is one of {INGEST_STATUSES}")
        super().__init__(f"ingest refused with {status}")
        self.status = status


__all__ = ["INGEST_STATUSES", "IngestRefusal", "MAX_INVENTORY_NAMES", "MAX_INVENTORY_NAME_LENGTH"]
