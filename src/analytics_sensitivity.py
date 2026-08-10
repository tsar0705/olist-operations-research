"""Phase 2.8 — validated sensitivity-analysis engine.

The engine formalizes the Phase 1.8 experiments around the validated
optimization services. It intentionally excludes the invalid monotonicity
test on the full Model 1 transportation component.

Experiments:
1. Model 1 fixed facility cost
2. Model 1 capacity
3. Model 1 demand growth
4. Model 2 capacity
5. Model 1 transportation-cost scale
6. Model 1 fixed-cost × capacity grid
7. Corrected Model 1 transportation-only capacity benchmark
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import math
import numpy as np
import pandas as pd
from scipy.optimize import linprog

from ..optimization.scenarios import Scenario
from ..optimization.services import run_model1, run_model2


@dataclass(frozen=True)
class SensitivityConfig:
    fixed_cost_values: tuple[float, ...] = (
        0.0, 10_000.0, 25_000.0, 50_000.0, 75_000.0,
        100_000.0, 150_000.0, 200_000.0, 300_000.0, 500_000.0,
    )
    capacity_values: tuple[float, ...] = (
        0.50, 0.60, 0.75, 0.90, 1.00, 1.10, 1.20,
        1.30, 1.50, 1.75, 2.00,
    )
    demand_values: tuple[float, ...] = (0.80, 1.00, 1.10, 1.25, 1.50)
    transport_values: tuple[float, ...] = (0.50, 0.75, 1.00, 1.25, 1.50)
    grid_fixed_costs: tuple[float, ...] = (25_000.0, 50_000.0, 100_000.0)
    grid_capacities: tuple[float, ...] = (0.75, 1.00, 1.20, 1.50)


def _base_metadata(result, parameter_name, parameter_value):
    if result.validation is None:
        validation_passed = False
    else:
        validation_passed = bool(result.validation.passed)

    return {
        "parameter": parameter_name,
        "parameter_value": parameter_value,
        "feasible": result.objective_value is not None and validation_passed,
        "status": result.status,
        "validation_passed": validation_passed,
    }


def _model1_row(result, parameter_name, parameter_value):
    meta = _base_metadata(result, parameter_name, parameter_value)
    opened = result.metadata.get("opened_hubs", []) if result.metadata else []
    return {
        **meta,
        "opened_hubs": len(opened),
        "hub_states": ",".join(opened),
        "fixed_cost_total": result.fixed_cost,
        "transport_cost_total": result.transport_cost,
        "total_cost": result.objective_value,
    }


def _model2_row(result, parameter_name, parameter_value):
    meta = _base_metadata(result, parameter_name, parameter_value)
    used = []
    if result.utilization_table is not None and not result.utilization_table.empty:
        used = result.utilization_table.loc[
            result.utilization_table["used"], "state"
        ].tolist()
    return {
        **meta,
        "used_seller_states": len(used),
        "seller_states": ",".join(used),
        "total_cost": result.objective_value,
    }


def run_model1_fixed_cost(bundle, config=SensitivityConfig()):
    rows = []
    for fixed_cost in config.fixed_cost_values:
        scenario = Scenario(
            capacity_multiplier=1.20,
            fixed_cost_per_hub=float(fixed_cost),
            max_hubs=None,
            demand_multiplier=1.00,
            transport_cost_multiplier=1.00,
        )
        result = run_model1(
            bundle.demand_table,
            bundle.candidate_hubs,
            bundle.cost_matrix,
            scenario,
        )
        rows.append(_model1_row(result, "fixed_cost_per_hub", fixed_cost))
    return pd.DataFrame(rows)


def run_model1_capacity(bundle, config=SensitivityConfig()):
    rows = []
    for capacity in config.capacity_values:
        scenario = Scenario(
            capacity_multiplier=float(capacity),
            fixed_cost_per_hub=50_000.0,
            max_hubs=None,
            demand_multiplier=1.00,
            transport_cost_multiplier=1.00,
        )
        result = run_model1(
            bundle.demand_table,
            bundle.candidate_hubs,
            bundle.cost_matrix,
            scenario,
        )
        rows.append(_model1_row(result, "capacity_multiplier", capacity))
    return pd.DataFrame(rows)


def run_model1_demand_growth(bundle, config=SensitivityConfig()):
    rows = []
    for demand_multiplier in config.demand_values:
        scenario = Scenario(
            capacity_multiplier=1.20,
            fixed_cost_per_hub=50_000.0,
            max_hubs=None,
            demand_multiplier=float(demand_multiplier),
            transport_cost_multiplier=1.00,
        )
        result = run_model1(
            bundle.demand_table,
            bundle.candidate_hubs,
            bundle.cost_matrix,
            scenario,
        )
        rows.append(_model1_row(result, "demand_multiplier", demand_multiplier))
    return pd.DataFrame(rows)


def run_model2_capacity(bundle, config=SensitivityConfig()):
    rows = []
    for capacity in config.capacity_values:
        scenario = Scenario(
            capacity_multiplier=float(capacity),
            fixed_cost_per_hub=50_000.0,
            max_hubs=None,
            demand_multiplier=1.00,
            transport_cost_multiplier=1.00,
        )
        result = run_model2(
            bundle.demand_table,
            bundle.candidate_hubs,
            bundle.cost_matrix,
            scenario,
        )
        rows.append(_model2_row(result, "capacity_multiplier", capacity))
    return pd.DataFrame(rows)


def run_model1_transport_scale(bundle, config=SensitivityConfig()):
    rows = []
    for scale in config.transport_values:
        scenario = Scenario(
            capacity_multiplier=1.20,
            fixed_cost_per_hub=50_000.0,
            max_hubs=None,
            demand_multiplier=1.00,
            transport_cost_multiplier=float(scale),
        )
        result = run_model1(
            bundle.demand_table,
            bundle.candidate_hubs,
            bundle.cost_matrix,
            scenario,
        )
        rows.append(_model1_row(result, "transport_cost_multiplier", scale))
    return pd.DataFrame(rows)


def run_model1_fixed_capacity_grid(bundle, config=SensitivityConfig()):
    rows = []
    for fixed_cost in config.grid_fixed_costs:
        for capacity in config.grid_capacities:
            scenario = Scenario(
                capacity_multiplier=float(capacity),
                fixed_cost_per_hub=float(fixed_cost),
                max_hubs=None,
                demand_multiplier=1.00,
                transport_cost_multiplier=1.00,
            )
            result = run_model1(
                bundle.demand_table,
                bundle.candidate_hubs,
                bundle.cost_matrix,
                scenario,
            )
            row = _model1_row(result, "fixed_cost_x_capacity", f"{fixed_cost:g}|{capacity:g}")
            row["fixed_cost_per_hub"] = fixed_cost
            row["capacity_multiplier"] = capacity
            rows.append(row)
    return pd.DataFrame(rows)


def run_transport_only_capacity_benchmark(bundle, config=SensitivityConfig()):
    """Correct monotonicity benchmark from Phase 1.8.

    This deliberately removes fixed hub-opening costs and solves only the
    transportation allocation problem. With increasing capacities, the
    feasible region expands, so the optimal transport cost cannot increase.
    """
    demand = bundle.demand_table.copy()
    hubs = bundle.candidate_hubs.copy()
    cost = bundle.cost_matrix.copy()

    demand_states = demand["state"].tolist()
    hub_states = hubs["state"].tolist()
    D = demand.set_index("state")["demand_orders"].astype(float).to_dict()
    base_caps = hubs.set_index("state")["base_capacity_orders"].astype(float).to_dict()
    C = np.array([
        [float(cost.loc[cost["origin_state"] == h].iloc[0][d])
         for d in demand_states]
        for h in hub_states
    ])

    n_i, n_j = len(hub_states), len(demand_states)
    c = C.ravel()
    A_eq = np.zeros((n_j, n_i * n_j))
    for j in range(n_j):
        for i in range(n_i):
            A_eq[j, i * n_j + j] = 1.0
    b_eq = np.array([D[s] for s in demand_states], dtype=float)

    rows = []
    for multiplier in config.capacity_values:
        caps = np.array([
            math.ceil(base_caps[s] * multiplier) for s in hub_states
        ], dtype=float)
        A_ub = np.zeros((n_i, n_i * n_j))
        for i in range(n_i):
            for j in range(n_j):
                A_ub[i, i * n_j + j] = 1.0
        res = linprog(
            c=c,
            A_ub=A_ub,
            b_ub=caps,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=(0, None),
            method="highs",
        )
        rows.append({
            "capacity_multiplier": multiplier,
            "feasible": bool(res.success),
            "transport_only_optimum": float(res.fun) if res.success else np.nan,
            "status": str(res.message),
        })

    out = pd.DataFrame(rows)
    feasible_costs = out.loc[out["feasible"], "transport_only_optimum"].dropna()
    monotone = bool(np.all(np.diff(feasible_costs.to_numpy()) <= 1e-6))
    out.attrs["nonincreasing_pass"] = monotone
    return out


def run_all_sensitivity(bundle, config=SensitivityConfig()):
    return {
        "fixed_cost": run_model1_fixed_cost(bundle, config),
        "model1_capacity": run_model1_capacity(bundle, config),
        "demand_growth": run_model1_demand_growth(bundle, config),
        "model2_capacity": run_model2_capacity(bundle, config),
        "transport_scale": run_model1_transport_scale(bundle, config),
        "fixed_capacity_grid": run_model1_fixed_capacity_grid(bundle, config),
        "transport_only_capacity": run_transport_only_capacity_benchmark(bundle, config),
    }
