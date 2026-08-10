"""Minimal canonical-session cache contract used by Phase 2 optimization caching."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any


@dataclass
class CanonicalSession:
    dataset_fingerprint: str | None = None
    bundle: Any = None
    validation_report: Any = None
    model1_result: Any = None
    model2_result: Any = None
    sensitivity_results: Any = None
    optimization_cache: dict[str, Any] = field(default_factory=dict)


def make_dataset_fingerprint(payloads: dict[str, bytes]) -> str:
    digest = sha256()
    for name in sorted(payloads):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payloads[name])
        digest.update(b"\0")
    return digest.hexdigest()


def install_bundle(session: CanonicalSession, fingerprint: str, bundle: Any, validation_report: Any) -> bool:
    changed = session.dataset_fingerprint != fingerprint
    if changed:
        session.model1_result = None
        session.model2_result = None
        session.sensitivity_results = None
        session.optimization_cache.clear()
    session.dataset_fingerprint = fingerprint
    session.bundle = bundle
    session.validation_report = validation_report
    return changed


def scenario_cache_key(dataset_fingerprint: str, model_name: str, scenario: Any) -> str:
    payload = scenario.to_dict() if hasattr(scenario, "to_dict") else scenario
    return json.dumps(
        {"dataset_fingerprint": dataset_fingerprint, "model": model_name, "scenario": payload},
        sort_keys=True,
        default=str,
    )


def get_cached_result(session: CanonicalSession, key: str) -> Any:
    return session.optimization_cache.get(key)


def put_cached_result(session: CanonicalSession, key: str, result: Any) -> None:
    session.optimization_cache[key] = result
