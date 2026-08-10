"""
Phase 1.1 — Olist data ingestion and preprocessing.

This module is intentionally separated from the Streamlit application.
It validates the original Olist schemas, normalizes dates, aggregates
one-to-many tables safely, creates the order fact table, derives state
demand, builds geolocation centroids, and prepares historical seller
capacity.

No optimization assumptions (facility fixed cost, capacity multiplier,
or freight-rate coefficient) are hard-coded here.
"""

from pathlib import Path
import pandas as pd
import numpy as np

EXPECTED_COLUMNS = {
    "orders": ["order_id","customer_id","order_status","order_purchase_timestamp",
               "order_approved_at","order_delivered_carrier_date",
               "order_delivered_customer_date","order_estimated_delivery_date"],
    "order_items": ["order_id","order_item_id","product_id","seller_id",
                    "shipping_limit_date","price","freight_value"],
    "payments": ["order_id","payment_sequential","payment_type",
                 "payment_installments","payment_value"],
    "reviews": ["review_id","order_id","review_score","review_comment_title",
                "review_comment_message","review_creation_date",
                "review_answer_timestamp"],
    "products": ["product_id","product_category_name","product_name_lenght",
                 "product_description_lenght","product_photos_qty",
                 "product_weight_g","product_length_cm","product_height_cm",
                 "product_width_cm"],
    "sellers": ["seller_id","seller_zip_code_prefix","seller_city","seller_state"],
    "customers": ["customer_id","customer_unique_id","customer_zip_code_prefix",
                  "customer_city","customer_state"],
    "geolocation": ["geolocation_zip_code_prefix","geolocation_lat",
                    "geolocation_lng","geolocation_city","geolocation_state"],
    "category_translation": ["product_category_name","product_category_name_english"],
}

def load_olist(data_dir):
    data_dir = Path(data_dir)
    filenames = {
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
    data = {}
    for key, filename in filenames.items():
        path = data_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing Olist file: {path}")
        df = pd.read_csv(path)
        missing = set(EXPECTED_COLUMNS[key]) - set(df.columns)
        if missing:
            raise ValueError(f"{filename}: missing columns {sorted(missing)}")
        data[key] = df
    return data

def validate_references(data):
    checks = [
        ("order_items.order_id -> orders.order_id",
         data["order_items"]["order_id"], data["orders"]["order_id"]),
        ("order_items.product_id -> products.product_id",
         data["order_items"]["product_id"], data["products"]["product_id"]),
        ("order_items.seller_id -> sellers.seller_id",
         data["order_items"]["seller_id"], data["sellers"]["seller_id"]),
        ("payments.order_id -> orders.order_id",
         data["payments"]["order_id"], data["orders"]["order_id"]),
        ("reviews.order_id -> orders.order_id",
         data["reviews"]["order_id"], data["orders"]["order_id"]),
        ("orders.customer_id -> customers.customer_id",
         data["orders"]["customer_id"], data["customers"]["customer_id"]),
    ]
    return {
        name: int((~child.isin(set(parent))).sum())
        for name, child, parent in checks
    }

def build_order_fact(data):
    orders = data["orders"].copy()
    items = data["order_items"].copy()
    payments = data["payments"].copy()
    reviews = data["reviews"].copy()
    customers = data["customers"].copy()

    for col in [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    item_order = items.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        unique_products=("product_id", "nunique"),
        unique_sellers=("seller_id", "nunique"),
        product_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
    )

    payment_order = payments.groupby("order_id", as_index=False).agg(
        payment_value=("payment_value", "sum"),
        payment_count=("payment_sequential", "count"),
        max_installments=("payment_installments", "max"),
    )

    review_order = reviews.groupby("order_id", as_index=False).agg(
        review_count=("review_id", "nunique"),
        avg_review_score=("review_score", "mean"),
    )

    fact = (
        orders
        .merge(customers, on="customer_id", how="left", validate="one_to_one")
        .merge(item_order, on="order_id", how="left", validate="one_to_one")
        .merge(payment_order, on="order_id", how="left", validate="one_to_one")
        .merge(review_order, on="order_id", how="left", validate="one_to_one")
    )

    fact["delivery_days"] = (
        fact["order_delivered_customer_date"]
        - fact["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400.0

    fact["delivery_delay_days"] = (
        fact["order_delivered_customer_date"]
        - fact["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400.0

    fact["is_delivered"] = (
        fact["order_status"].eq("delivered")
        & fact["order_delivered_customer_date"].notna()
    )
    fact["is_late"] = fact["is_delivered"] & (fact["delivery_delay_days"] > 0)

    return fact

def build_state_coordinates(geolocation):
    geo = geolocation.drop_duplicates()
    return (
        geo.groupby("geolocation_state", as_index=False)
        .agg(
            latitude=("geolocation_lat", "mean"),
            longitude=("geolocation_lng", "mean"),
            coordinate_observations=("geolocation_zip_code_prefix", "size"),
        )
        .rename(columns={"geolocation_state": "state"})
    )

def build_state_demand(order_fact, state_coordinates):
    demand = order_fact.groupby("customer_state", as_index=False).agg(
        orders=("order_id", "nunique"),
        product_value=("product_value", "sum"),
        freight_value=("freight_value", "sum"),
        avg_freight_per_order=("freight_value", "mean"),
        avg_delivery_days=("delivery_days", "mean"),
        delivered_orders=("is_delivered", "sum"),
        late_orders=("is_late", "sum"),
        unique_customers=("customer_unique_id", "nunique"),
    )
    demand["delivery_rate_pct"] = demand["delivered_orders"] / demand["orders"] * 100
    demand["late_rate_pct_of_delivered"] = np.where(
        demand["delivered_orders"] > 0,
        demand["late_orders"] / demand["delivered_orders"] * 100,
        np.nan,
    )
    return demand.merge(
        state_coordinates[["state", "latitude", "longitude"]],
        left_on="customer_state",
        right_on="state",
        how="left",
    ).drop(columns=["state"])

def build_seller_state_capacity(data):
    items = data["order_items"]
    sellers = data["sellers"]
    seller_volume = items.groupby("seller_id", as_index=False).agg(
        historical_items=("order_item_id", "count"),
        historical_orders=("order_id", "nunique"),
        product_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
    )
    seller = sellers.merge(
        seller_volume, on="seller_id", how="left", validate="one_to_one"
    ).fillna({
        "historical_items": 0,
        "historical_orders": 0,
        "product_value": 0,
        "freight_value": 0,
    })
    return seller.groupby("seller_state", as_index=False).agg(
        sellers=("seller_id", "nunique"),
        historical_items=("historical_items", "sum"),
        historical_orders=("historical_orders", "sum"),
        product_value=("product_value", "sum"),
        freight_value=("freight_value", "sum"),
    )
