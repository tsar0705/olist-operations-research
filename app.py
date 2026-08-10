"""Olist Operations Research Dashboard — Phase 2.12 release entry point.

The entry point intentionally contains orchestration only. Analytical logic,
validation, optimization, geography, and result construction live below src/.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.app_state import AppState
from src.config import DEFAULT_CONFIG
from src.release import release_ready, run_release_checks
from src.ui.release_status import render_release_status_page
from src.ui.theme import apply_theme

st.set_page_config(
    page_title=DEFAULT_CONFIG.page_title,
    page_icon="📦",
    layout=DEFAULT_CONFIG.layout,
    initial_sidebar_state="expanded",
)
apply_theme()

if "app_state" not in st.session_state:
    st.session_state.app_state = AppState()

# Scenario is intentionally imported lazily. A partial deployment should still
# be able to open the release diagnostics page rather than crashing on startup.
if "scenario" not in st.session_state:
    try:
        from src.optimization import Scenario
        st.session_state.scenario = Scenario()
    except Exception as exc:
        st.session_state.scenario = None
        st.session_state._scenario_import_error = str(exc)

state = st.session_state.app_state
bundle = state.canonical_bundle

st.sidebar.title("📦 Olist OR Dashboard")
st.sidebar.caption(f"Phase 2.12 · v{DEFAULT_CONFIG.version}")

if bundle is not None and bundle.is_valid:
    st.sidebar.success("Dataset: READY")
    st.sidebar.caption(f"Fingerprint: {state.dataset_fingerprint}")
else:
    st.sidebar.warning("Dataset: NOT READY")
    st.sidebar.caption("Upload and validate all nine Olist tables.")

if st.sidebar.button("Reset session", width="stretch", help="Clear the active dataset and all transient optimization results."):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

page = st.sidebar.radio(
    "Navigation",
    [
        "Dataset Upload & Validation",
        "Model 1 — Facility Location",
        "Model 2 — Seller Assignment",
        "Sensitivity Analysis",
        "Model Comparison & Downloads",
        "Release & Architecture Status",
    ],
)


def _render_page(page_name: str, import_path: str, function_name: str) -> None:
    """Import a page only when selected and surface missing runtime cleanly."""
    try:
        module = __import__(import_path, fromlist=[function_name])
        getattr(module, function_name)()
    except Exception as exc:
        st.error(f"{page_name} is unavailable in this deployment.")
        with st.expander("Technical details", expanded=False):
            st.code(str(exc))
        st.info("Open **Release & Architecture Status** for the deployment checklist.")


if page == "Dataset Upload & Validation":
    _render_page("Dataset Upload & Validation", "src.ui.upload_page", "render_upload_page")
elif page == "Model 1 — Facility Location":
    _render_page("Model 1", "src.ui.model1_page", "render_model1_page")
elif page == "Model 2 — Seller Assignment":
    _render_page("Model 2", "src.ui.model2_page", "render_model2_page")
elif page == "Sensitivity Analysis":
    _render_page("Sensitivity Analysis", "src.ui.sensitivity_page", "render_sensitivity_page")
elif page == "Model Comparison & Downloads":
    _render_page("Model Comparison & Downloads", "src.ui.comparison_page", "render_comparison_page")
else:
    render_release_status_page()

st.markdown("---")
st.caption(
    "Olist OR Dashboard · validated Phase 1 analytical pipeline · "
    "Streamlit presentation layer"
)
