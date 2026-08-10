"""Application configuration for the final Olist operations-research dashboard."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardConfig:
    title: str = "Olist Operations Research Dashboard"
    page_title: str = "Olist OR Dashboard"
    layout: str = "wide"
    version: str = "2.12"


DEFAULT_CONFIG = DashboardConfig()

# The final dashboard accepts the nine source tables used by the validated
# Phase 1 pipeline.  The UI never substitutes synthetic/demo data.
REQUIRED_OLIST_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}
