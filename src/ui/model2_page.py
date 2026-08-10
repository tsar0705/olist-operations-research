"""Phase 2.7 — Model 2 dashboard page."""
from __future__ import annotations

import math
import pandas as pd
import streamlit as st

from ..app_state import get_app_state
from ..optimization.scenarios import Scenario
from ..optimization.services import run_model2_from_bundle
from ..optimization.cache import run_cached
from .result_visualizations import render_model2_result_visuals, render_result_downloads


def _money(v: float | None) -> str:
    return "—" if v is None else f"R$ {v:,.2f}"


def render_model2_page() -> None:
    state = get_app_state(st)
    bundle = state.canonical_bundle
    st.title("Model 2 — Seller-State Assignment")
    st.caption("Capacitated single-source assignment: each customer state is assigned to exactly one existing seller state.")
    if bundle is None or not bundle.is_valid:
        st.warning("Dataset not ready. Validate all nine Olist tables before running Model 2.")
        return

    st.subheader("Scenario controls")
    current = state.metadata.get("model2_scenario", Scenario())
    capacity_multiplier = st.slider("Seller capacity multiplier", 0.50, 2.00,
                                     float(current.capacity_multiplier), 0.05,
                                     help="Scales the historical seller-state capacity proxy used by Model 2.")
    scenario = Scenario(capacity_multiplier=float(capacity_multiplier), fixed_cost_per_hub=0.0,
                        max_hubs=None, demand_multiplier=1.0, transport_cost_multiplier=1.0)
    scenario.validate()
    state.metadata["model2_scenario"] = scenario

    with st.expander("Model formulation", expanded=False):
        st.markdown(r"""
**Decision variable**

$$z_{ij} \in \{0,1\}$$

$z_{ij}=1$ means seller state $i$ serves all demand in customer state $j$.

**Objective**

$$\min \sum_i\sum_j c_{ij}D_jz_{ij}$$

**Single-source constraint**

$$\sum_i z_{ij}=1 \quad \forall j$$

**Capacity constraint**

$$\sum_jD_jz_{ij}\le Cap_i \quad \forall i$$

Unlike Model 1, Model 2 has no facility-opening decision and does not split a customer state's demand.
        """)

    st.divider()
    if st.button("Solve Model 2", type="primary", width="stretch"):
        with st.spinner("Solving the capacitated single-source assignment model…"):
            try:
                result, cache_hit = run_cached(state, "model2", scenario,
                    lambda: run_model2_from_bundle(bundle, scenario))
                state.model2_result = result
                state.metadata["model2_cache_hit"] = cache_hit
                state.metadata["model2_scenario"] = scenario
            except Exception as exc:
                state.model2_result = None
                st.error(f"Model 2 could not be solved: {exc}")
                return

    result = state.model2_result
    if result is None:
        st.info("Choose the capacity scenario and click **Solve Model 2**.")
        return
    st.subheader("Optimization result")
    cache_hit = state.metadata.get("model2_cache_hit", False)
    st.caption("Result retrieved from scenario cache." if cache_hit else "Result freshly solved and stored in the scenario cache.")
    if result.is_optimal and result.is_valid:
        st.success("VALID OPTIMAL SOLUTION — solver and Model 2 validation checks passed.")
    elif result.is_optimal:
        st.error("Solver returned an optimal solution, but Model 2 validation failed. The result is not accepted.")
    else:
        st.error(f"Optimization did not return an optimal solution: {result.status}")
        for message in result.validation.messages:
            st.write(f"• {message}")
        return

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Assignment cost", _money(result.objective_value))
    m2.metric("Seller states used", f"{result.metadata['seller_states_used_count']}")
    m3.metric("Customer states", f"{result.metadata['customer_states']}")
    m4.metric("Demand", f"{result.metadata['demand_total']:,.0f}")
    m5.metric("Capacity", f"{result.metadata['capacity_total']:,.0f}")
    st.markdown("**Seller states used:** " + ", ".join(result.metadata["seller_states_used"]))

    st.divider()
    st.subheader("Seller-state capacity utilization")
    util = result.utilization_table.copy()
    st.dataframe(util, width="stretch", hide_index=True)
    used_util = util[util["used"]]
    if not used_util.empty:
        st.bar_chart(used_util.set_index("state")["utilization_pct"])
    st.download_button("Download seller capacity solution", util.to_csv(index=False).encode(),
                       "model2_seller_capacity_utilization.csv", "text/csv")

    st.divider()
    st.subheader("Customer-state assignments")
    assignment = result.decision_table.copy()
    st.dataframe(assignment, width="stretch", hide_index=True)
    st.download_button("Download assignments", assignment.to_csv(index=False).encode(),
                       "model2_customer_state_assignments.csv", "text/csv")

    st.divider()
    st.subheader("Geographic assignment network")
    render_model2_result_visuals(bundle, result)
    render_result_downloads(result, "model2")

    st.divider()
    st.subheader("Validation")
    checks_df = pd.DataFrame([{"Check": k.replace("_", " ").title(), "Result": "PASS" if v else "FAIL"}
                              for k, v in result.validation.checks.items()])
    st.dataframe(checks_df, width="stretch", hide_index=True)
    for message in result.validation.messages:
        st.warning(message)

    with st.expander("Objective reconciliation", expanded=False):
        st.dataframe(pd.DataFrame([{
            "assignment_cost": result.transport_cost,
            "reconstructed_total": result.metadata["reconstructed_objective"],
            "solver_objective": result.objective_value,
            "difference": result.objective_value - result.metadata["reconstructed_objective"],
        }]), width="stretch", hide_index=True)

    with st.expander("Scenario and model metadata", expanded=False):
        st.json({"scenario": scenario.to_dict(),
                 "seller_states_used": result.metadata["seller_states_used"],
                 "dataset_fingerprint": state.dataset_fingerprint,
                 "calibration_model": bundle.metadata.get("calibration_model"),
                 "calibration_coefficients": bundle.metadata.get("calibration_coefficients"),
                 "single_source": True})
