"""Phase 2.10 — Model 1 vs Model 2 comparison helpers.

This module is intentionally analytical/presentation-neutral. It compares two
validated OptimizationResult objects on common metrics and makes structural
differences explicit so that a lower objective is not misinterpreted when the
models have different cost structures.
"""
from __future__ import annotations

from typing import Any
import pandas as pd


COMMON_SCENARIO_KEYS = (
    "capacity_multiplier",
    "demand_multiplier",
    "transport_cost_multiplier",
)


def _valid(result: Any) -> bool:
    return bool(result is not None and result.is_optimal and result.is_valid)


def _scenario_dict(result: Any) -> dict[str, Any]:
    metadata = getattr(result, "metadata", {}) or {}
    scenario = metadata.get("scenario", {})
    if hasattr(scenario, "to_dict"):
        return scenario.to_dict()
    return dict(scenario) if isinstance(scenario, dict) else {}


def scenario_compatibility(model1: Any, model2: Any) -> dict[str, Any]:
    """Check whether the two displayed results share the same common scenario inputs."""
    s1 = _scenario_dict(model1)
    s2 = _scenario_dict(model2)
    comparisons = {}
    for key in COMMON_SCENARIO_KEYS:
        comparisons[key] = s1.get(key) == s2.get(key)
    return {
        "compatible": bool(comparisons) and all(comparisons.values()),
        "checks": comparisons,
        "model1_scenario": s1,
        "model2_scenario": s2,
    }


def _demand_total(result: Any) -> float:
    metadata = getattr(result, "metadata", {}) or {}
    value = metadata.get("demand_total")
    if value is not None:
        return float(value)
    table = getattr(result, "decision_table", None)
    if table is not None and not table.empty and "demand_orders" in table.columns:
        return float(table["demand_orders"].sum())
    flow = getattr(result, "flow_table", None)
    if flow is not None and not flow.empty and "orders_shipped" in flow.columns:
        return float(flow.groupby("destination_state")["orders_shipped"].sum().sum())
    return 0.0


def _util_stats(table: Any) -> tuple[float | None, float | None, int]:
    if table is None or table.empty or "utilization_pct" not in table.columns:
        return None, None, 0
    values = pd.to_numeric(table["utilization_pct"], errors="coerce").dropna()
    if values.empty:
        return None, None, 0
    if "used" in table.columns:
        used = int(table["used"].fillna(False).sum())
    else:
        used = int((values > 0).sum())
    return float(values.max()), float(values.mean()), used


def _model1_split_stats(result: Any) -> tuple[int, int]:
    flow = getattr(result, "flow_table", None)
    if flow is None or flow.empty:
        return 0, 0
    required = {"destination_state", "origin_hub", "orders_shipped"}
    if not required.issubset(flow.columns):
        return 0, 0
    positive = flow[pd.to_numeric(flow["orders_shipped"], errors="coerce") > 1e-9]
    by_customer = positive.groupby("destination_state")["origin_hub"].nunique()
    split = int((by_customer > 1).sum())
    return split, int(len(by_customer))


def build_model_comparison(model1: Any, model2: Any) -> pd.DataFrame:
    """Return one-row common-metric comparison for two validated results."""
    if not _valid(model1):
        raise ValueError("Model 1 result must be optimal and validation-passed before comparison.")
    if not _valid(model2):
        raise ValueError("Model 2 result must be optimal and validation-passed before comparison.")

    demand = max(_demand_total(model1), _demand_total(model2))
    m1_max_util, m1_avg_util, m1_used = _util_stats(model1.utilization_table)
    m2_max_util, m2_avg_util, m2_used = _util_stats(model2.utilization_table)
    m1_split, m1_customer_count = _model1_split_stats(model1)

    m1_transport = float(model1.transport_cost or 0.0)
    m2_transport = float(model2.transport_cost or 0.0)
    m1_total = float(model1.objective_value or 0.0)
    m2_total = float(model2.objective_value or 0.0)

    row = {
        "dataset_fingerprint": (model1.metadata or {}).get("dataset_fingerprint")
        or (model2.metadata or {}).get("dataset_fingerprint"),
        "demand_orders": demand,
        "model1_total_objective": m1_total,
        "model2_total_objective": m2_total,
        "model1_fixed_cost": float(model1.fixed_cost or 0.0),
        "model1_transport_cost": m1_transport,
        "model2_transport_cost": m2_transport,
        "transport_cost_delta_model2_minus_model1": m2_transport - m1_transport,
        "transport_cost_delta_pct_vs_model1": ((m2_transport - m1_transport) / m1_transport * 100.0)
        if m1_transport else None,
        "model1_total_cost_per_order": m1_total / demand if demand else None,
        "model2_total_cost_per_order": m2_total / demand if demand else None,
        "model1_transport_cost_per_order": m1_transport / demand if demand else None,
        "model2_transport_cost_per_order": m2_transport / demand if demand else None,
        "model1_hubs_opened": int((model1.metadata or {}).get("opened_hub_count", m1_used)),
        "model2_seller_states_used": int((model2.metadata or {}).get("seller_states_used_count", m2_used)),
        "model1_max_utilization_pct": m1_max_util,
        "model2_max_utilization_pct": m2_max_util,
        "model1_mean_utilization_pct": m1_avg_util,
        "model2_mean_utilization_pct": m2_avg_util,
        "model1_split_customer_states": m1_split,
        "model1_customer_states_with_flow": m1_customer_count,
        "model2_single_source": True,
        "model1_allows_split_flows": True,
        "model1_has_facility_opening_cost": True,
        "model2_has_facility_opening_cost": False,
    }
    return pd.DataFrame([row])


def build_structural_comparison() -> pd.DataFrame:
    """Return the fixed conceptual differences between the two formulations."""
    return pd.DataFrame([
        {"Dimension": "Facility decision", "Model 1": "Opens/closes candidate hubs", "Model 2": "No opening decision; seller states already exist"},
        {"Dimension": "Demand sourcing", "Model 1": "Can split a customer state's demand across hubs", "Model 2": "Each customer state is single-sourced"},
        {"Dimension": "Capacity", "Model 1": "Hub capacity linked to opening", "Model 2": "Seller-state capacity"},
        {"Dimension": "Fixed facility cost", "Model 1": "Included as scenario assumption", "Model 2": "Not included"},
        {"Dimension": "Primary objective", "Model 1": "Fixed facility cost + transportation", "Model 2": "Transportation only"},
    ])
