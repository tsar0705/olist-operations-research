"""Phase 2.8 — Sensitivity Analysis page."""
from __future__ import annotations

import io
import pandas as pd
import streamlit as st
import plotly.express as px

from ..app_state import get_app_state
from ..analytics.sensitivity import (
    SensitivityConfig,
    run_model1_fixed_cost,
    run_model1_capacity,
    run_model1_demand_growth,
    run_model2_capacity,
    run_model1_transport_scale,
    run_model1_fixed_capacity_grid,
    run_transport_only_capacity_benchmark,
)


def _download_csv(df: pd.DataFrame, filename: str, key: str):
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )


def _show_table(df: pd.DataFrame, key: str):
    st.dataframe(df, width="stretch", hide_index=True)
    _download_csv(df, f"{key}.csv", key=f"download_{key}")


def _run_experiment(label, fn, bundle, config):
    cache_key = f"sensitivity::{label}"
    state = st.session_state
    if cache_key not in state:
        with st.spinner(f"Running {label}..."):
            state[cache_key] = fn(bundle, config)
    return state[cache_key]


def _metric_summary(df, cost_col="total_cost"):
    feasible = df[df["feasible"]].copy()
    if feasible.empty:
        return
    cols = st.columns(3)
    cols[0].metric("Scenarios tested", len(df))
    cols[1].metric("Feasible", int(df["feasible"].sum()))
    cols[2].metric("Infeasible", int((~df["feasible"]).sum()))


def render_sensitivity_page():
    st.title("Sensitivity Analysis")
    st.caption(
        "Phase 1.8 scenario experiments on the validated Olist optimization models."
    )

    state = get_app_state(st)
    bundle = state.canonical_bundle
    if bundle is None or not bundle.is_valid:
        st.warning("Load and validate the Olist dataset before running sensitivity analysis.")
        return

    st.info(
        "Sensitivity parameters are scenario assumptions. The Phase 1.4 calibrated "
        "transportation model remains the cost baseline; the transport multiplier is "
        "used only for controlled stress testing."
    )

    with st.expander("Reference scenario and analytical definitions", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Reference capacity", "1.20×")
        c2.metric("Reference fixed cost", "R$ 50,000")
        c3.metric("Reference demand", "1.00×")
        c4.metric("Reference transport", "1.00×")

        st.markdown(
            """
            **Model 1:** fixed facility cost + calibrated transportation cost, with
            continuous split flows and capacity-linked hub opening.

            **Model 2:** binary single-source seller-state assignment with seller-state
            capacity.

            **Important:** the full Model 1 transportation component is *not* expected
            to be monotone in capacity because capacity, hub opening, fixed cost, and
            transportation are optimized jointly.
            """
        )

    tabs = st.tabs([
        "M1 — Fixed Cost",
        "M1 — Capacity",
        "M1 — Demand Growth",
        "M2 — Capacity",
        "M1 — Transport Stress",
        "M1 — Cost × Capacity",
        "Validation Benchmark",
    ])

    config = SensitivityConfig()

    # --------------------------------------------------------------
    # M1 fixed cost
    # --------------------------------------------------------------
    with tabs[0]:
        st.subheader("Model 1 — Fixed Facility Cost Sensitivity")
        st.caption(
            "Capacity stays at 1.20×. The fixed facility cost is varied to show "
            "the trade-off between fewer hubs and higher transport cost."
        )
        if st.button("Run fixed-cost sensitivity", key="run_fixed_cost"):
            st.session_state.pop("sensitivity::fixed_cost", None)
        df = _run_experiment("fixed_cost", run_model1_fixed_cost, bundle, config)
        _metric_summary(df)

        feasible = df[df["feasible"]]
        if not feasible.empty:
            fig = px.line(
                feasible,
                x="parameter_value",
                y="total_cost",
                markers=True,
                labels={
                    "parameter_value": "Fixed cost per hub (R$)",
                    "total_cost": "Total cost (R$)",
                },
                title="Total cost vs fixed facility cost",
            )
            st.plotly_chart(fig, width="stretch")

            fig2 = px.line(
                feasible,
                x="parameter_value",
                y="opened_hubs",
                markers=True,
                labels={
                    "parameter_value": "Fixed cost per hub (R$)",
                    "opened_hubs": "Opened hubs",
                },
                title="Hub count vs fixed facility cost",
            )
            st.plotly_chart(fig2, width="stretch")

        _show_table(df, "model1_fixed_cost_sensitivity")

    # --------------------------------------------------------------
    # M1 capacity
    # --------------------------------------------------------------
    with tabs[1]:
        st.subheader("Model 1 — Capacity Sensitivity")
        st.caption(
            "Fixed cost remains R$50,000/hub. Low capacity can make the facility "
            "location model infeasible."
        )
        if st.button("Run Model 1 capacity sensitivity", key="run_m1_capacity"):
            st.session_state.pop("sensitivity::model1_capacity", None)
        df = _run_experiment("model1_capacity", run_model1_capacity, bundle, config)
        _metric_summary(df)

        feasible = df[df["feasible"]]
        if not feasible.empty:
            fig = px.line(
                feasible,
                x="parameter_value",
                y="total_cost",
                markers=True,
                labels={
                    "parameter_value": "Capacity multiplier",
                    "total_cost": "Total cost (R$)",
                },
                title="Model 1 total cost vs capacity",
            )
            st.plotly_chart(fig, width="stretch")

        _show_table(df, "model1_capacity_sensitivity")

    # --------------------------------------------------------------
    # Demand growth
    # --------------------------------------------------------------
    with tabs[2]:
        st.subheader("Model 1 — Demand Growth")
        st.caption(
            "Demand is scaled while the 1.20× capacity scenario is held fixed. "
            "This identifies the point where the network becomes infeasible."
        )
        if st.button("Run demand-growth sensitivity", key="run_demand"):
            st.session_state.pop("sensitivity::demand_growth", None)
        df = _run_experiment("demand_growth", run_model1_demand_growth, bundle, config)
        _metric_summary(df)

        feasible = df[df["feasible"]]
        if not feasible.empty:
            fig = px.line(
                feasible,
                x="parameter_value",
                y="total_cost",
                markers=True,
                labels={
                    "parameter_value": "Demand multiplier",
                    "total_cost": "Total cost (R$)",
                },
                title="Model 1 total cost vs demand growth",
            )
            st.plotly_chart(fig, width="stretch")

        _show_table(df, "model1_demand_growth_sensitivity")

    # --------------------------------------------------------------
    # M2 capacity
    # --------------------------------------------------------------
    with tabs[3]:
        st.subheader("Model 2 — Seller Capacity Sensitivity")
        st.caption(
            "Single-source assignment can remain infeasible even when aggregate "
            "capacity is sufficient, because complete customer states cannot be split."
        )
        if st.button("Run Model 2 capacity sensitivity", key="run_m2_capacity"):
            st.session_state.pop("sensitivity::model2_capacity", None)
        df = _run_experiment("model2_capacity", run_model2_capacity, bundle, config)
        _metric_summary(df)

        feasible = df[df["feasible"]]
        if not feasible.empty:
            fig = px.line(
                feasible,
                x="parameter_value",
                y="total_cost",
                markers=True,
                labels={
                    "parameter_value": "Capacity multiplier",
                    "total_cost": "Assignment cost (R$)",
                },
                title="Model 2 assignment cost vs capacity",
            )
            st.plotly_chart(fig, width="stretch")

        _show_table(df, "model2_capacity_sensitivity")

    # --------------------------------------------------------------
    # Transport stress
    # --------------------------------------------------------------
    with tabs[4]:
        st.subheader("Model 1 — Transportation-Cost Stress Test")
        st.caption(
            "Scales the Phase 1.4 calibrated transportation cost matrix without "
            "changing the underlying calibration."
        )
        if st.button("Run transport-cost stress", key="run_transport"):
            st.session_state.pop("sensitivity::transport_scale", None)
        df = _run_experiment("transport_scale", run_model1_transport_scale, bundle, config)
        _metric_summary(df)

        feasible = df[df["feasible"]]
        if not feasible.empty:
            fig = px.line(
                feasible,
                x="parameter_value",
                y="total_cost",
                markers=True,
                labels={
                    "parameter_value": "Transportation cost multiplier",
                    "total_cost": "Total cost (R$)",
                },
                title="Model 1 total cost under transport-cost stress",
            )
            st.plotly_chart(fig, width="stretch")

        _show_table(df, "model1_transport_cost_sensitivity")

    # --------------------------------------------------------------
    # Grid
    # --------------------------------------------------------------
    with tabs[5]:
        st.subheader("Model 1 — Fixed Cost × Capacity Grid")
        st.caption(
            "A two-parameter scenario surface for managerial interpretation."
        )
        if st.button("Run fixed-cost × capacity grid", key="run_grid"):
            st.session_state.pop("sensitivity::fixed_capacity_grid", None)
        df = _run_experiment(
            "fixed_capacity_grid",
            run_model1_fixed_capacity_grid,
            bundle,
            config,
        )
        _metric_summary(df)

        feasible = df[df["feasible"]]
        if not feasible.empty:
            pivot = feasible.pivot_table(
                index="capacity_multiplier",
                columns="fixed_cost_per_hub",
                values="total_cost",
                aggfunc="first",
            )
            st.dataframe(pivot.style.format("R$ {:,.0f}"), width="stretch")

        _show_table(df, "model1_fixed_cost_capacity_grid")

    # --------------------------------------------------------------
    # Corrected validation benchmark
    # --------------------------------------------------------------
    with tabs[6]:
        st.subheader("Corrected Capacity-Monotonicity Benchmark")
        st.caption(
            "This is the valid Phase 1.8 monotonicity test: remove fixed hub-opening "
            "costs and solve transportation only."
        )
        if st.button("Run validation benchmark", key="run_benchmark"):
            st.session_state.pop("sensitivity::transport_only_capacity", None)
        df = _run_experiment(
            "transport_only_capacity",
            run_transport_only_capacity_benchmark,
            bundle,
            config,
        )

        feasible = df[df["feasible"]]
        if not feasible.empty:
            monotone = bool(df.attrs.get("nonincreasing_pass", False))
            if monotone:
                st.success(
                    "PASS — transportation-only optimum is non-increasing as capacity relaxes."
                )
            else:
                st.error("FAIL — transportation-only monotonicity check did not pass.")

            fig = px.line(
                feasible,
                x="capacity_multiplier",
                y="transport_only_optimum",
                markers=True,
                labels={
                    "capacity_multiplier": "Capacity multiplier",
                    "transport_only_optimum": "Transportation-only optimum (R$)",
                },
                title="Valid capacity monotonicity benchmark",
            )
            st.plotly_chart(fig, width="stretch")

        _show_table(df, "model1_transport_only_capacity_benchmark")

    st.divider()
    st.subheader("Interpretation guide")
    st.markdown(
        """
        - **Fixed cost ↑:** opening hubs becomes more expensive, so the optimizer
          tends to consolidate into fewer hubs while accepting more transportation.
        - **Capacity ↑:** the feasible region expands, but the *full Model 1
          transportation component* need not decrease because the optimal hub
          configuration can change.
        - **Demand ↑:** total capacity remains fixed, so sufficiently large growth
          can make the model infeasible.
        - **Model 2 capacity:** feasibility is stricter because a customer state is
          assigned whole to one seller state.
        - **Transport stress:** shows how robust the selected network is to a
          multiplicative change in calibrated transportation costs.
        """
    )
