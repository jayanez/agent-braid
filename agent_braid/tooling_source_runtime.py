# SPDX-License-Identifier: AGPL-3.0-only
"""Concrete cache-to-supervisor adapter; acquisition stays outside the consumer.

Authenticity depends on the explicitly installed cache receipt verifier and
reviewed procedure files. Neither labels nor an authenticated DTO create trust.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable

from . import tooling_registration_v6 as registration
from . import tooling_source_observer as sources
from . import tooling_supervisor as supervisor
from .tooling_subscription import SubscriptionError


class CachedSourceRuntime:
    """Fast observer and verifier over one externally authenticated source cache.

    Caller telemetry remains subject to the independent cost/stop verifier.
    No acquisition callback or provider/UI call runs in either consumer method.
    Refreshes must already be published by the separately serialized producer.
    """

    def __init__(self, cache: sources.SourceObserverCache,
                 binding: registration.SourceRouteBinding, *,
                 procedures: sources.ProcedureFiles,
                 telemetry: Callable, utc_now: Callable = lambda: datetime.now(timezone.utc)):
        binding.validate()
        if not isinstance(cache, sources.SourceObserverCache) or cache.binding != binding.binding:
            raise sources.SourceObserverError("cache and source route binding differ")
        if registration._canonical(sources._thaw(cache.contract)) != registration._canonical(binding.contract):
            raise sources.SourceObserverError("cache source contract differs from frozen route")
        if not callable(telemetry) or not callable(utc_now):
            raise sources.SourceObserverError("explicit telemetry and UTC clock are required")
        core = binding.binding
        # Check procedure identity once at trusted installation. Acquisition and
        # witness authentication belong to cache's independently installed verifier.
        sources._pinned_file(procedures.source, core.observer_source_sha256, private=False)
        sources._pinned_file(procedures.verifier, core.observer_verifier_sha256, private=False)
        self.source_ref, self.source_sha256 = core.observer_source_ref, core.observer_source_sha256
        self.verifier_ref, self.verifier_sha256 = core.observer_verifier_ref, core.observer_verifier_sha256
        self._cache, self._binding = cache, binding
        self._telemetry, self._utc_now = telemetry, utc_now

    def _read(self, identity, final):
        if identity is not None and identity.birth is None:
            raise sources.SourceObserverError("exact kernel birth is required")
        return self._cache.read(now=self._utc_now(), expected_binding=self._binding.binding,
            phase="prelaunch" if identity is None else ("completed" if final else "running"),
            process_id=None if identity is None else identity.pid,
            process_birth_sha256=None if identity is None else supervisor._process_birth_sha256(identity.birth))

    def observe(self, identity, elapsed, final):
        snapshot = self._telemetry(identity, elapsed, final)
        if not isinstance(snapshot, supervisor.TelemetrySnapshot):
            raise sources.SourceObserverError("typed local telemetry is required")
        if snapshot.subscription is not None or snapshot.native_route is not None or snapshot.operational_route is not None:
            raise sources.SourceObserverError("source telemetry cannot mix legacy route observations")
        return replace(snapshot, source_route=self._read(identity, final))

    def verify_source_observation(self, observation, binding, identity, request, final):
        if binding != self._binding or supervisor._source_route_binding(request) != binding:
            raise SubscriptionError("supervisor source route differs from installed cache")
        current = self._read(identity, final)
        if not isinstance(observation, sources.SourceObservation) or observation.as_dict() != current.as_dict():
            raise SubscriptionError("source observation is absent, forged, invalidated or superseded")
        return None
