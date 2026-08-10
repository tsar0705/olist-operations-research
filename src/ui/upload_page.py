"""Phase 2.3 — Dataset upload and validation page."""
from __future__ import annotations

import streamlit as st

from ..config import REQUIRED_OLIST_FILES
from ..data.upload_validation import (
    FileValidation,
    all_required_files_uploaded,
    all_schemas_valid,
    build_bundle_from_uploads,
    validate_uploaded_files,
)

UPLOAD_LABELS = {
    "orders": "Orders",
    "order_items": "Order items",
    "payments": "Payments",
    "reviews": "Reviews",
    "products": "Products",
    "sellers": "Sellers",
    "customers": "Customers",
    "geolocation": "Geolocation",
    "category_translation": "Category translation",
}


def _file_table(results: list[FileValidation]):
    rows = []
    for item in results:
        if not item.uploaded:
            status = "MISSING"
        elif item.error:
            status = "ERROR"
        elif item.missing_columns:
            status = "INVALID SCHEMA"
        elif item.rows == 0:
            status = "EMPTY"
        else:
            status = "READY"
        rows.append(
            {
                "Table": UPLOAD_LABELS[item.key],
                "Expected filename": item.filename,
                "Rows": item.rows if item.uploaded else "—",
                "Columns": item.columns if item.uploaded else "—",
                "Status": status,
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)


def _show_schema_errors(results: list[FileValidation]):
    for item in results:
        if item.missing_columns:
            st.error(
                f"**{item.filename}** is missing required columns: "
                + ", ".join(item.missing_columns)
            )
        if item.error:
            st.error(f"**{item.filename}**: {item.error}")
        if item.uploaded and item.extra_columns:
            st.caption(
                f"{item.filename}: {len(item.extra_columns)} extra column(s) detected; "
                "extra columns are allowed by the Phase 1 schema contract."
            )


def render_upload_page():
    st.title("Dataset Upload & Validation")
    st.caption(
        "Phase 2.3 — load the real Olist dataset, validate its schema, then run "
        "the validated Phase 1.1–1.4 pipeline."
    )

    st.info(
        "The final dashboard does not use synthetic/demo data. All nine Olist "
        "source tables are required before the analytical engine can be marked ready."
    )

    st.subheader("1. Upload the nine Olist tables")
    uploaded_files = {}
    columns = st.columns(3)
    for index, (key, filename) in enumerate(REQUIRED_OLIST_FILES.items()):
        with columns[index % 3]:
            uploaded_files[key] = st.file_uploader(
                UPLOAD_LABELS[key],
                type=["csv"],
                key=f"olist_upload_{key}",
                help=f"Required file: {filename}",
            )

    results = validate_uploaded_files(uploaded_files)
    _file_table(results)
    _show_schema_errors(results)

    required_ok = all_required_files_uploaded(results)
    schema_ok = all_schemas_valid(results)

    st.subheader("2. Validation gates")
    gate_cols = st.columns(3)
    with gate_cols[0]:
        if required_ok:
            st.success("✓ All nine files uploaded")
        else:
            st.warning("Waiting for all nine files")
    with gate_cols[1]:
        if schema_ok:
            st.success("✓ Required schemas valid")
        else:
            st.warning("Schema validation incomplete")
    with gate_cols[2]:
        bundle = st.session_state.app_state.canonical_data
        if bundle is not None and bundle.is_valid:
            st.success("✓ Canonical dataset ready")
        else:
            st.info("Not processed yet")

    st.subheader("3. Run the Phase 1 validation pipeline")
    st.caption(
        "This step materializes the uploads temporarily and calls the same "
        "Phase 1 service used by the optimization layer."
    )

    if not required_ok or not schema_ok:
        st.button(
            "Validate dataset",
            disabled=True,
            width="stretch",
            help="Upload all nine files and fix schema errors first.",
        )
    else:
        if st.button("Validate dataset", type="primary", width="stretch"):
            with st.spinner("Running Olist ingestion, geography, demand/capacity and cost validation…"):
                try:
                    bundle = build_bundle_from_uploads(uploaded_files)
                    st.session_state.app_state.canonical_data = bundle
                    st.session_state.app_state.raw_data = bundle.raw_data
                    st.session_state.app_state.validation_report = {
                        "reference_checks": bundle.reference_checks,
                        "canonical_checks": bundle.canonical_checks,
                        "dataset_fingerprint": bundle.dataset_fingerprint,
                    }
                    st.session_state.app_state.order_fact = bundle.order_fact
                    st.session_state.app_state.state_coordinates = bundle.state_coordinates
                    st.session_state.app_state.distance_matrix = bundle.distance_matrix_long
                    st.session_state.app_state.demand_table = bundle.demand_table
                    st.session_state.app_state.seller_capacity = bundle.seller_capacity
                    st.session_state.app_state.candidate_hubs = bundle.candidate_hubs
                    st.session_state.app_state.cost_matrix = bundle.cost_matrix

                    if bundle.is_valid:
                        st.success("Dataset validated successfully. The canonical Phase 1 dataset is ready.")
                    else:
                        st.error("The canonical dataset failed one or more validation checks. Optimization is blocked.")
                except Exception as exc:
                    st.session_state.app_state.canonical_data = None
                    st.session_state.app_state.validation_report = {"error": str(exc)}
                    st.error(f"Dataset validation failed: {exc}")

    bundle = st.session_state.app_state.canonical_data
    if bundle is not None:
        st.divider()
        st.subheader("Validation result")
        if bundle.is_valid:
            st.success("DATASET READY — all Phase 1 canonical checks passed.")
            metric_cols = st.columns(5)
            metric_cols[0].metric("Orders", f"{bundle.demand_table['demand_orders'].sum():,.0f}")
            metric_cols[1].metric("Customer states", len(bundle.demand_table))
            metric_cols[2].metric("Seller states", len(bundle.candidate_hubs))
            metric_cols[3].metric("Optimization lanes", len(bundle.candidate_hubs) * len(bundle.demand_table))
            metric_cols[4].metric("Cost model", bundle.metadata["calibration_model"])

            with st.expander("Reference-integrity checks", expanded=False):
                st.json(bundle.reference_checks)
            with st.expander("Canonical checks", expanded=False):
                st.json(bundle.canonical_checks)
            with st.expander("Dataset metadata", expanded=False):
                st.json(bundle.metadata)
            st.caption(f"Dataset fingerprint: `{bundle.dataset_fingerprint}`")
        else:
            st.error("DATASET NOT READY — optimization remains blocked.")
            with st.expander("Validation details", expanded=True):
                st.json(bundle.canonical_checks)
