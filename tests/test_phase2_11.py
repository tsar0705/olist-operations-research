"""Phase 2.11 — end-to-end dashboard integration/contract tests.

The production dashboard is a Streamlit application backed by the complete
Phase 1/2 package. These tests intentionally separate:

1. source-level integration contracts that can run without Streamlit/solver
   binaries in a minimal CI environment; and
2. optional Streamlit AppTest smoke tests, which run automatically when the
   real dashboard dependencies are installed.

The end-to-end contract follows the architecture:
9 uploads -> schema gate -> canonical bundle -> Model 1/2 -> sensitivity ->
comparison/downloads, while invalid canonical data must block optimization.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP = ROOT / "app.py"
UPLOAD = ROOT / "src/ui/upload_page.py"
MODEL1 = ROOT / "src/ui/model1_page.py"
MODEL2 = ROOT / "src/ui/model2_page.py"
SENSITIVITY = ROOT / "src/ui/sensitivity_page.py"
COMPARISON_PAGE = ROOT / "src/ui/comparison_page.py"
COMPARISON = ROOT / "src/optimization/comparison.py"


def _tree(path: Path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _call_names(path: Path) -> set[str]:
    tree = _tree(path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def test_navigation_reaches_every_phase_2_page():
    source = _source(APP)
    required = [
        "Dataset Upload & Validation",
        "Model 1 — Facility Location",
        "Model 2 — Seller Assignment",
        "Sensitivity Analysis",
        "Model Comparison & Downloads",
        "Architecture Status",
    ]
    for page in required:
        assert page in source

    # Phase 2.12 intentionally lazy-loads pages so a partial deployment can
    # still open release diagnostics instead of crashing during import.
    assert "src.ui.comparison_page" in source
    assert 'elif page == "Model Comparison & Downloads":' in source
    assert "render_comparison_page" in source


def test_app_is_orchestration_only_and_contains_no_prototype_geo_or_solver_logic():
    source = _source(APP)
    forbidden = [
        "STATE_COORDS",
        "LpProblem",
        "LpVariable",
        "haversine",
        "build_demo_demand",
        "build_demo_seller_capacity",
        "synthetic",
    ]
    for token in forbidden:
        assert token not in source


def test_upload_page_has_nine_file_gate_and_validation_pipeline():
    source = _source(UPLOAD)
    assert "REQUIRED_OLIST_FILES" in source
    assert "validate_uploaded_files" in source
    assert "all_required_files_uploaded" in source
    assert "all_schemas_valid" in source
    assert "build_bundle_from_uploads" in source
    assert "if not required_ok or not schema_ok:" in source
    assert "st.button(" in source and "disabled=True" in source
    assert "bundle.is_valid" in source


def test_optimization_pages_block_invalid_canonical_data():
    for path in (MODEL1, MODEL2, SENSITIVITY):
        source = _source(path)
        assert "bundle is None or not bundle.is_valid" in source
        assert "return" in source


def test_models_use_service_boundary_and_scenario_cache():
    m1 = _source(MODEL1)
    m2 = _source(MODEL2)
    assert "run_model1_from_bundle" in m1
    assert "run_model2_from_bundle" in m2
    assert "run_cached" in m1
    assert "run_cached" in m2
    assert "Scenario(" in m1
    assert "Scenario(" in m2


def test_comparison_page_is_read_only_and_requires_two_valid_results():
    source = _source(COMPARISON_PAGE)
    assert "state.model1_result" in source
    assert "state.model2_result" in source
    assert "if m1 is None or m2 is None:" in source
    assert "m1.is_optimal and m1.is_valid" in source
    assert "m2.is_optimal and m2.is_valid" in source
    assert "build_model_comparison" in source
    assert "build_structural_comparison" in source
    assert "_build_export_zip" in source
    # The comparison page must not run either optimization itself.
    assert "run_model1" not in source
    assert "run_model2" not in source


def test_download_contract_covers_comparison_structural_and_all_result_tables():
    source = _source(COMPARISON_PAGE)
    required_exports = [
        "model_comparison.csv",
        "structural_comparison.csv",
        "model1_decision_table.csv",
        "model1_utilization.csv",
        "model1_flows.csv",
        "model2_decision_table.csv",
        "model2_utilization.csv",
        "model2_flows.csv",
        "run_metadata.json",
    ]
    for filename in required_exports:
        assert filename in source


def test_phase_2_10_comparison_still_works_as_part_of_phase_2_11():
    from src.optimization.comparison import build_model_comparison, scenario_compatibility
    from src.optimization.result_models import OptimizationResult, ValidationResult

    def result(model: str, objective: float, transport: float, scenario: dict):
        return OptimizationResult(
            model=model,
            status="Optimal",
            objective_value=objective,
            validation=ValidationResult(True, {"all": True}, []),
            transport_cost=transport,
            metadata={
                "demand_total": 100,
                "scenario": scenario,
                "opened_hub_count": 2 if model == "model1" else 0,
                "seller_states_used_count": 2 if model == "model2" else 0,
            },
            utilization_table=pd.DataFrame({
                "state": ["SP", "RJ"],
                "utilization_pct": [80.0, 50.0],
                "used": [True, True],
            }),
            flow_table=(
                pd.DataFrame({
                    "origin_hub": ["SP", "RJ"],
                    "destination_state": ["MG", "MG"],
                    "orders_shipped": [40, 60],
                    "cost_per_order": [10, 12],
                }) if model == "model1" else None
            ),
        )

    scenario = {
        "capacity_multiplier": 1.2,
        "demand_multiplier": 1.0,
        "transport_cost_multiplier": 1.0,
    }
    m1 = result("model1", 1500, 1200, scenario)
    m2 = result("model2", 1400, 1400, scenario)

    comparison = build_model_comparison(m1, m2)
    assert comparison.iloc[0]["transport_cost_delta_model2_minus_model1"] == 200
    assert scenario_compatibility(m1, m2)["compatible"] is True


def test_optional_streamlit_app_test_smoke():
    """Run a real Streamlit AppTest smoke test when dependencies are present.

    The current minimal execution environment does not ship Streamlit, so this
    test is intentionally skipped there rather than replacing a real UI test
    with a fake Streamlit implementation.
    """
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=10)
    at.run()

    assert not at.exception
    assert any("Dataset Upload & Validation" in option for option in at.sidebar.radio[0].options)


def test_optional_streamlit_navigation_smoke():
    """Exercise navigation labels through AppTest when the full environment exists."""
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=10).run()
    radio = at.sidebar.radio[0]
    labels = set(radio.options)
    assert "Model Comparison & Downloads" in labels
    assert "Sensitivity Analysis" in labels
