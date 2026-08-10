from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.data.phase1_service import build_canonical_bundle
from src.optimization.services import run_model1_from_bundle, run_model2_from_bundle
from src.optimization.scenarios import Scenario
from src.optimization.comparison import build_model_comparison

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_OLIST_FILES = {
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
}


def _is_olist_dir(path: Path) -> bool:
    return path.exists() and path.is_dir() and REQUIRED_OLIST_FILES.issubset(
        {p.name for p in path.iterdir() if p.is_file()}
    )


def _find_olist_data_dir() -> Path | None:
    env_dir = os.getenv("OLIST_DATA_DIR")
    if env_dir and _is_olist_dir(Path(env_dir).expanduser()):
        return Path(env_dir).expanduser()

    # Supports:
    # release_root/
    # ├── data/  <-- the user's nine CSVs
    # └── live/  <-- this project when extracted as instructed
    candidates = [
        ROOT / "data",
        ROOT.parent / "data",
    ]

    for candidate in candidates:
        if _is_olist_dir(candidate):
            return candidate

    return None


DATA = _find_olist_data_dir()

pytestmark = pytest.mark.skipif(
    DATA is None,
    reason=(
        "Olist data not found. Set OLIST_DATA_DIR to the folder containing "
        "the nine Olist CSV files, or place them in ../data relative to live/."
    ),
)


def test_full_olist_phase1_to_phase2_pipeline():
    bundle = build_canonical_bundle(DATA)

    assert bundle.is_valid
    assert int(bundle.demand_table["demand_orders"].sum()) == 99441
    assert len(bundle.demand_table) == 27
    assert len(bundle.candidate_hubs) == 23
    # 23 hub rows × (1 origin_state metadata column + 27 destination-state columns).
    assert bundle.cost_matrix.shape == (23, 28)
    assert "origin_state" in bundle.cost_matrix.columns
    assert len([c for c in bundle.cost_matrix.columns if c != "origin_state"]) == 27

    scenario = Scenario()
    m1 = run_model1_from_bundle(bundle, scenario)
    m2 = run_model2_from_bundle(bundle, scenario)

    assert m1.is_optimal and m1.is_valid
    assert m2.is_optimal and m2.is_valid

    comparison = build_model_comparison(m1, m2)
    assert len(comparison) == 1
    assert int(comparison.iloc[0]["demand_orders"]) == 99441
