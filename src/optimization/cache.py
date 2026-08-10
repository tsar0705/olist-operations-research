"""Scenario-aware optimization cache built on the canonical session."""
from __future__ import annotations
from typing import Any, Callable
from src.data.session_cache import CanonicalSession, get_cached_result, put_cached_result, scenario_cache_key

def run_cached(session: CanonicalSession, model_name: str, scenario: Any, solver_fn: Callable[[], Any]) -> tuple[Any, bool]:
    if not session.dataset_fingerprint:
        raise RuntimeError("Cannot run optimization without a dataset fingerprint.")
    key = scenario_cache_key(session.dataset_fingerprint, model_name, scenario)
    cached = get_cached_result(session, key)
    if cached is not None:
        return cached, True
    result = solver_fn()
    put_cached_result(session, key, result)
    return result, False
