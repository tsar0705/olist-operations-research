"""Phase 2.12 — final UI polish and release-hardening contract tests."""
from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP = ROOT / "app.py"
CONFIG = ROOT / "src/config.py"
RELEASE = ROOT / "src/release.py"
STATUS = ROOT / "src/ui/release_status.py"
THEME = ROOT / "src/ui/theme.py"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_app_entrypoint_is_thin_and_release_hardened():
    text = source(APP)
    for forbidden in ("STATE_COORDS", "LpProblem", "LpVariable", "haversine", "build_demo_demand"):
        assert forbidden not in text
    assert "_render_page" in text
    assert "Reset session" in text
    assert "Release & Architecture Status" in text
    ast.parse(text)


def test_release_diagnostics_do_not_require_analytical_imports():
    text = source(RELEASE)
    assert "importlib.util.find_spec" in text
    assert "REQUIRED_PROJECT_FILES" in text
    assert "release_ready" in text
    ast.parse(text)


def test_release_status_page_exposes_blocking_checks():
    text = source(STATUS)
    assert "RELEASE BLOCKED" in text
    assert "run_release_checks" in text
    assert "release_ready" in text
    assert "Release rules" in text


def test_config_has_all_nine_real_olist_sources():
    text = source(CONFIG)
    expected = [
        "olist_orders_dataset.csv",
        "olist_order_items_dataset.csv",
        "olist_order_payments_dataset.csv",
        "olist_order_reviews_dataset.csv",
        "olist_products_dataset.csv",
        "olist_sellers_dataset.csv",
        "olist_customers_dataset.csv",
        "olist_geolocation_dataset.csv",
        "product_category_name_translation.csv",
    ]
    for filename in expected:
        assert filename in text


def test_theme_contains_consistent_dashboard_primitives():
    text = source(THEME)
    assert "apply_theme" in text
    assert "section_intro" in text
    assert "status_card" in text
    assert "st.markdown" in text


def test_release_manifest_does_not_claim_demo_data_support():
    text = source(ROOT / "README.md")
    assert "does **not** use synthetic/demo data" in text
    assert "missing modules as blockers" in text
