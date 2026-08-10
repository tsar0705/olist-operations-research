"""Phase 2.10 — downloads and Model 1 vs Model 2 comparison page."""
from __future__ import annotations

import io
import json
import zipfile

import pandas as pd
import streamlit as st

from ..app_state import get_app_state
from ..optimization.comparison import (
    build_model_comparison,
    build_structural_comparison,
    scenario_compatibility,
)


def _csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, indent=2, default=str).encode("utf-8")


def _download(label: str, data: bytes, filename: str, mime: str, key: str):
    st.download_button(label, data=data, file_name=filename, mime=mime, key=key)


def _build_export_zip(state, comparison: pd.DataFrame, structural: pd.DataFrame) -> bytes:
    m1 = state.model1_result
    m2 = state.model2_result
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("model_comparison.csv", _csv_bytes(comparison))
        archive.writestr("structural_comparison.csv", _csv_bytes(structural))
        if m1 is not None:
            if m1.decision_table is not None:
                archive.writestr("model1_decision_table.csv", _csv_bytes(m1.decision_table))
            if m1.utilization_table is not None:
                archive.writestr("model1_utilization.csv", _csv_bytes(m1.utilization_table))
            if m1.flow_table is not None:
                archive.writestr("model1_flows.csv", _csv_bytes(m1.flow_table))
        if m2 is not None:
            if m2.decision_table is not None:
                archive.writestr("model2_decision_table.csv", _csv_bytes(m2.decision_table))
            if m2.utilization_table is not None:
                archive.writestr("model2_utilization.csv", _csv_bytes(m2.utilization_table))
            if m2.flow_table is not None:
                archive.writestr("model2_flows.csv", _csv_bytes(m2.flow_table))
        archive.writestr(
            "run_metadata.json",
            _json_bytes({
                "dataset_fingerprint": state.dataset_fingerprint,
                "model1_scenario": (m1.metadata or {}).get("scenario", {}) if m1 else {},
                "model2_scenario": (m2.metadata or {}).get("scenario", {}) if m2 else {},
                "model1_validation": getattr(m1.validation, "checks", {}) if m1 else {},
                "model2_validation": getattr(m2.validation, "checks", {}) if m2 else {},
            }),
        )
    return buffer.getvalue()


def render_comparison_page():
    state = get_app_state(st)
    st.title("Model Comparison & Downloads")
    st.caption("Phase 2.10 — compare the validated Model 1 and Model 2 scenarios and export the full result package.")

    m1 = state.model1_result
    m2 = state.model2_result
    if m1 is None or m2 is None:
        st.warning("Solve both Model 1 and Model 2 before comparing them.")
        st.info("The comparison intentionally does not run either optimization model itself.")
        return

    if not (m1.is_optimal and m1.is_valid):
        st.error("Model 1 is not an accepted optimal/validated result. Comparison is blocked.")
        return
    if not (m2.is_optimal and m2.is_valid):
        st.error("Model 2 is not an accepted optimal/validated result. Comparison is blocked.")
        return

    compatibility = scenario_compatibility(m1, m2)
    if compatibility["compatible"]:
        st.success("Comparable scenario inputs: capacity, demand and transportation multipliers match.")
    else:
        st.warning(
            "The two results were solved under different common scenario inputs. "
            "The comparison is still shown, but transport-cost differences should not be treated as an apples-to-apples scenario benchmark."
        )

    comparison = build_model_comparison(m1, m2)
    structural = build_structural_comparison()

    st.subheader("Decision summary")
    row = comparison.iloc[0]
    cols = st.columns(4)
    cols[0].metric("Model 1 total objective", f"R$ {row['model1_total_objective']:,.2f}")
    cols[1].metric("Model 2 objective", f"R$ {row['model2_total_objective']:,.2f}")
    cols[2].metric("M1 transport cost", f"R$ {row['model1_transport_cost']:,.2f}")
    cols[3].metric("M2 transport cost", f"R$ {row['model2_transport_cost']:,.2f}")

    st.subheader("Common-metric comparison")
    display = pd.DataFrame({
        "Metric": [
            "Total objective",
            "Transportation cost",
            "Cost per order — transportation",
            "Maximum utilization",
            "Mean utilization",
            "Facilities / seller states used",
            "Customer states split across sources",
        ],
        "Model 1": [
            f"R$ {row['model1_total_objective']:,.2f}",
            f"R$ {row['model1_transport_cost']:,.2f}",
            f"R$ {row['model1_transport_cost_per_order']:,.2f}",
            f"{row['model1_max_utilization_pct']:.2f}%" if row['model1_max_utilization_pct'] is not None else "—",
            f"{row['model1_mean_utilization_pct']:.2f}%" if row['model1_mean_utilization_pct'] is not None else "—",
            int(row['model1_hubs_opened']),
            int(row['model1_split_customer_states']),
        ],
        "Model 2": [
            f"R$ {row['model2_total_objective']:,.2f}",
            f"R$ {row['model2_transport_cost']:,.2f}",
            f"R$ {row['model2_transport_cost_per_order']:,.2f}",
            f"{row['model2_max_utilization_pct']:.2f}%" if row['model2_max_utilization_pct'] is not None else "—",
            f"{row['model2_mean_utilization_pct']:.2f}%" if row['model2_mean_utilization_pct'] is not None else "—",
            int(row['model2_seller_states_used']),
            "0 (single-source)",
        ],
    })
    st.dataframe(display, width="stretch", hide_index=True)

    delta = row["transport_cost_delta_model2_minus_model1"]
    if delta < 0:
        st.info(f"Model 2 has lower transportation cost by R$ {-delta:,.2f} under the displayed scenarios.")
    elif delta > 0:
        st.info(f"Model 1 has lower transportation cost by R$ {delta:,.2f} under the displayed scenarios.")
    else:
        st.info("The two models have the same transportation cost under the displayed scenarios.")

    st.subheader("Why the objectives are not identical")
    st.dataframe(structural, width="stretch", hide_index=True)
    st.caption(
        "Model 1 includes a fixed facility-opening component, while Model 2 is transportation-only. "
        "Therefore the total objectives should not be interpreted as a pure apples-to-apples transport comparison."
    )

    with st.expander("Scenario compatibility details", expanded=False):
        st.json(compatibility)

    st.subheader("Downloads")
    c1, c2, c3 = st.columns(3)
    with c1:
        _download("Download comparison CSV", _csv_bytes(comparison), "model_comparison.csv", "text/csv", "comparison_csv")
    with c2:
        _download("Download structural CSV", _csv_bytes(structural), "structural_comparison.csv", "text/csv", "structural_csv")
    with c3:
        package = _build_export_zip(state, comparison, structural)
        _download("Download complete result package", package, "olist_model_results_phase2_10.zip", "application/zip", "complete_package")

    st.markdown("**Individual result tables**")
    download_cols = st.columns(6)
    items = [
        (m1, "decision_table", "model1_decision_table.csv", "M1 decision", "m1_decision"),
        (m1, "utilization_table", "model1_utilization.csv", "M1 utilization", "m1_util"),
        (m1, "flow_table", "model1_flows.csv", "M1 flows", "m1_flows"),
        (m2, "decision_table", "model2_decision_table.csv", "M2 decision", "m2_decision"),
        (m2, "utilization_table", "model2_utilization.csv", "M2 utilization", "m2_util"),
        (m2, "flow_table", "model2_flows.csv", "M2 flows", "m2_flows"),
    ]
    for col, (result, attr, filename, label, key) in zip(download_cols, items):
        with col:
            table = getattr(result, attr)
            if table is not None:
                _download(label, _csv_bytes(table), filename, "text/csv", key)
            else:
                st.caption(f"{label}: unavailable")
