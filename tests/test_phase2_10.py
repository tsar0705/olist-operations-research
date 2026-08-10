from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.optimization.comparison import build_model_comparison, build_structural_comparison, scenario_compatibility
from src.optimization.result_models import OptimizationResult, ValidationResult


def _result(model, objective, transport, fixed=0.0, metadata=None, decision=None, util=None, flow=None):
    return OptimizationResult(
        model=model,
        status="Optimal",
        objective_value=objective,
        validation=ValidationResult(True, {"all": True}, []),
        fixed_cost=fixed,
        transport_cost=transport,
        decision_table=decision,
        utilization_table=util,
        flow_table=flow,
        metadata=metadata or {},
    )


def test_comparison_uses_common_transport_metrics_and_split_count():
    util = pd.DataFrame({"state": ["SP", "RJ"], "utilization_pct": [80.0, 50.0], "used": [True, True]})
    m1 = _result(
        "model1", 1500, 1200, 300,
        metadata={"demand_total": 100, "opened_hub_count": 2, "scenario": {"capacity_multiplier": 1.2, "demand_multiplier": 1.0, "transport_cost_multiplier": 1.0}},
        util=util,
        flow=pd.DataFrame({"origin_hub": ["SP", "RJ", "SP"], "destination_state": ["MG", "MG", "SP"], "orders_shipped": [40, 60, 10], "cost_per_order": [10, 12, 1]}),
    )
    m2 = _result(
        "model2", 1400, 1400,
        metadata={"demand_total": 100, "seller_states_used_count": 2, "scenario": {"capacity_multiplier": 1.2, "demand_multiplier": 1.0, "transport_cost_multiplier": 1.0}},
        util=util,
        decision=pd.DataFrame({"assigned_seller_state": ["SP", "RJ"], "customer_state": ["MG", "SP"], "demand_orders": [60, 40], "cost_per_order": [12, 1]}),
    )
    df = build_model_comparison(m1, m2)
    row = df.iloc[0]
    assert row["model1_split_customer_states"] == 1
    assert row["transport_cost_delta_model2_minus_model1"] == 200
    assert row["model1_transport_cost_per_order"] == 12


def test_scenario_compatibility_detects_mismatch():
    base = {"capacity_multiplier": 1.2, "demand_multiplier": 1.0, "transport_cost_multiplier": 1.0}
    m1 = _result("model1", 1, 1, metadata={"scenario": base})
    m2 = _result("model2", 1, 1, metadata={"scenario": {**base, "capacity_multiplier": 1.5}})
    result = scenario_compatibility(m1, m2)
    assert not result["compatible"]
    assert not result["checks"]["capacity_multiplier"]


def test_structural_comparison_has_expected_dimensions():
    df = build_structural_comparison()
    assert set(df["Dimension"]) == {
        "Facility decision", "Demand sourcing", "Capacity", "Fixed facility cost", "Primary objective"
    }
