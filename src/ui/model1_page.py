"""Phase 2.6 — Model 1 dashboard page."""
from __future__ import annotations

import math
import pandas as pd
import streamlit as st

from ..app_state import get_app_state
from ..optimization.scenarios import Scenario
from ..optimization.services import run_model1_from_bundle
from ..optimization.cache import run_cached
from .result_visualizations import render_model1_result_visuals, render_result_downloads


def _money(v: float | None) -> str:
    return "—" if v is None else f"R$ {v:,.2f}"


def render_model1_page() -> None:
    state = get_app_state(st)
    bundle = state.canonical_bundle

    st.title("Model 1 — Facility Location + Transportation")
    st.caption(
        "Capacitated facility-location MILP: choose which candidate hubs to open and how to route demand from open hubs."
    )

    if bundle is None or not bundle.is_valid:
        st.warning("Dataset not ready. Validate all nine Olist tables before running Model 1.")
        return

    st.subheader("Scenario controls")
    current = state.metadata.get("model1_scenario", Scenario())
    c1, c2, c3 = st.columns(3)
    with c1:
        fixed_cost = st.number_input(
            "Fixed cost per opened hub (R$)",
            min_value=0.0,
            value=float(current.fixed_cost_per_hub),
            step=5000.0,
            help="Scenario assumption; Olist does not contain observed facility operating costs.",
        )
    with c2:
        capacity_multiplier = st.slider(
            "Capacity multiplier",
            min_value=0.50,
            max_value=2.00,
            value=float(current.capacity_multiplier),
            step=0.05,
        )
    with c3:
        max_hubs = st.number_input(
            "Maximum hubs",
            min_value=1,
            max_value=len(bundle.candidate_hubs),
            value=current.max_hubs if current.max_hubs is not None else len(bundle.candidate_hubs),
            step=1,
            help="Set to the number of candidates to impose no effective upper restriction.",
        )

    no_hub_limit = st.checkbox(
        "No explicit maximum-hub constraint",
        value=current.max_hubs is None,
    )
    scenario = Scenario(
        capacity_multiplier=float(capacity_multiplier),
        fixed_cost_per_hub=float(fixed_cost),
        max_hubs=None if no_hub_limit else int(max_hubs),
        demand_multiplier=1.0,
        transport_cost_multiplier=1.0,
    )
    scenario.validate()
    state.metadata["model1_scenario"] = scenario

    with st.expander("Model formulation", expanded=False):
        st.markdown(
            r"""
**Decision variables**

- $y_i \in \{0,1\}$ — whether candidate hub $i$ is opened.
- $x_{ij} \ge 0$ — orders shipped from hub $i$ to customer state $j$.

**Objective**

$$\min \sum_i F y_i + \sum_i\sum_j c_{ij}x_{ij}$$

**Demand:** every customer state's demand must be satisfied.

**Capacity:** shipments leaving hub $i$ cannot exceed its scenario capacity when $y_i=1$.

**Optional hub limit:** $\sum_i y_i \le p$.

The transportation costs are the validated Phase 1.4 calibration; fixed facility cost is an explicit scenario assumption.
            """
        )

    st.divider()
    if st.button("Solve Model 1", type="primary", width="stretch"):
        with st.spinner("Solving the capacitated facility-location model…"):
            try:
                result, cache_hit = run_cached(
                    state,
                    "model1",
                    scenario,
                    lambda: run_model1_from_bundle(bundle, scenario),
                )
                state.model1_result = result
                state.metadata["model1_cache_hit"] = cache_hit
                state.metadata["model1_scenario"] = scenario
            except Exception as exc:
                state.model1_result = None
                st.error(f"Model 1 could not be solved: {exc}")
                return

    result = state.model1_result
    if result is None:
        st.info("Choose the scenario parameters and click **Solve Model 1**.")
        return

    st.subheader("Optimization result")
    cache_hit = state.metadata.get("model1_cache_hit", False)
    st.caption("Result retrieved from scenario cache." if cache_hit else "Result freshly solved and stored in the scenario cache.")

    if result.is_optimal and result.is_valid:
        st.success("VALID OPTIMAL SOLUTION — solver and model validation checks passed.")
    elif result.is_optimal:
        st.error("Solver returned an optimal solution, but model validation failed. The result is not accepted.")
    else:
        st.error(f"Optimization did not return an optimal solution: {result.status}")
        if result.validation.messages:
            for msg in result.validation.messages:
                st.write(f"• {msg}")
        return

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total objective", _money(result.objective_value))
    m2.metric("Fixed cost", _money(result.fixed_cost))
    m3.metric("Transportation cost", _money(result.transport_cost))
    m4.metric("Opened hubs", f"{result.metadata['opened_hub_count']}")
    m5.metric("Demand", f"{result.metadata['demand_total']:,.0f}")

    opened = result.metadata["opened_hubs"]
    st.markdown("**Opened hubs:** " + ", ".join(opened))

    st.divider()
    st.subheader("Hub utilization")
    util = result.utilization_table.copy()
    st.dataframe(util, width="stretch", hide_index=True)
    st.bar_chart(util.set_index("state")["utilization_pct"])
    st.download_button(
        "Download hub solution",
        data=result.decision_table.to_csv(index=False).encode("utf-8"),
        file_name="model1_hub_solution.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Shipment plan")
    flow = result.flow_table
    st.dataframe(flow, width="stretch", hide_index=True)
    st.download_button(
        "Download shipment plan",
        data=flow.to_csv(index=False).encode("utf-8"),
        file_name="model1_shipment_plan.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Geographic network")
    render_model1_result_visuals(bundle, result)
    render_result_downloads(result, "model1")

    st.divider()
    st.subheader("Validation")
    checks_df = pd.DataFrame([
        {"Check": key.replace("_", " ").title(), "Result": "PASS" if value else "FAIL"}
        for key, value in result.validation.checks.items()
    ])
    st.dataframe(checks_df, width="stretch", hide_index=True)
    if result.validation.messages:
        for message in result.validation.messages:
            st.warning(message)

    with st.expander("Objective reconciliation", expanded=False):
        reconciliation = pd.DataFrame([{
            "fixed_cost": result.fixed_cost,
            "transportation_cost": result.transport_cost,
            "reconstructed_total": result.metadata["reconstructed_objective"],
            "solver_objective": result.objective_value,
            "difference": result.objective_value - result.metadata["reconstructed_objective"],
        }])
        st.dataframe(reconciliation, width="stretch", hide_index=True)

    with st.expander("Scenario and model metadata", expanded=False):
        st.json({
            "scenario": scenario.to_dict(),
            "opened_hubs": opened,
            "dataset_fingerprint": state.dataset_fingerprint,
            "calibration_model": bundle.metadata.get("calibration_model"),
            "calibration_coefficients": bundle.metadata.get("calibration_coefficients"),
        })
