from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.phase1_service import build_canonical_bundle
from src.optimization.services import run_model1_from_bundle, run_model2_from_bundle
from src.optimization.scenarios import Scenario
from src.optimization.comparison import build_model_comparison

REQUIRED = {
    "olist_customers_dataset.csv", "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv", "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv", "olist_orders_dataset.csv",
    "olist_products_dataset.csv", "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
}

def find_data_dir() -> Path:
    candidates = []
    if os.getenv("OLIST_DATA_DIR"):
        candidates.append(Path(os.environ["OLIST_DATA_DIR"]).expanduser())
    candidates.extend([ROOT / "data", ROOT.parent / "data"])
    for d in candidates:
        if d.exists() and REQUIRED.issubset({p.name for p in d.iterdir() if p.is_file()}):
            return d
    raise SystemExit(
        "Real Olist data not found. Set OLIST_DATA_DIR to the folder containing "
        "the nine required Olist CSV files."
    )

DATA = find_data_dir()
b = build_canonical_bundle(DATA)
assert b.is_valid
m1 = run_model1_from_bundle(b, Scenario())
m2 = run_model2_from_bundle(b, Scenario())
assert m1.is_optimal and m1.is_valid
assert m2.is_optimal and m2.is_valid
c = build_model_comparison(m1, m2)
assert len(c) == 1
print("Olist data directory:", DATA)
print("Olist bundle: PASS")
print("Orders:", int(b.demand_table.demand_orders.sum()))
print("Customer states:", len(b.demand_table))
print("Seller states:", len(b.candidate_hubs))
print("Lanes:", len(b.candidate_hubs) * len(b.demand_table))
print("Model 1:", m1.objective_value, m1.metadata["opened_hubs"])
print("Model 2:", m2.objective_value, m2.metadata["seller_states_used_count"])
print("Comparison:", len(c), "row")
