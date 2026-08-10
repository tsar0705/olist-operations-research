"""
Phase 2.2 — Service boundary around the validated Phase 1 pipeline.

This module turns the Phase 1.1–1.4 analytical pipeline into one canonical
service that the Streamlit application can call. The UI does not perform
Olist joins, geography calculations, or transportation-cost construction.

The transportation calibration profile is loaded from the Phase 1.4 JSON
artifact. Its coefficients are configuration/data, not duplicated model
logic.
"""

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any
import json

import numpy as np
import pandas as pd

from .olist_preprocessing import (
    EXPECTED_COLUMNS,
    load_olist,
    validate_references,
    build_order_fact,
    build_state_demand,
    build_seller_state_capacity,
)
from .geography import (
    build_zip_coordinates,
    build_state_coordinates,
    build_state_distance_matrix,
    map_zip_to_entities,
)
from ..validation.data_checks import validate_canonical_inputs


DEFAULT_CALIBRATION_PROFILE = Path(__file__).resolve().parents[2] / "phase1_outputs" / "PHASE_1_4_CALIBRATION.json"


@dataclass(frozen=True)
class CanonicalDataBundle:
    """Canonical objects consumed by the dashboard and optimization services."""
    raw_data: dict[str, pd.DataFrame]
    order_fact: pd.DataFrame
    zip_coordinates: pd.DataFrame
    state_coordinates: pd.DataFrame
    distance_matrix_long: pd.DataFrame
    demand_table: pd.DataFrame
    seller_capacity: pd.DataFrame
    candidate_hubs: pd.DataFrame
    cost_matrix: pd.DataFrame
    calibration_profile: dict[str, Any]
    reference_checks: dict[str, int]
    canonical_checks: dict[str, bool]
    source_files: dict[str, str]
    dataset_fingerprint: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return (
            all(v == 0 for v in self.reference_checks.values())
            and all(self.canonical_checks.values())
        )


def _fingerprint_files(paths: dict[str, Path]) -> str:
    digest = sha256()
    for key, path in sorted(paths.items()):
        digest.update(key.encode("utf-8"))
        digest.update(path.name.encode("utf-8"))
        digest.update(str(path.stat().st_size).encode("utf-8"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _calibration_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    # /phase2_dashboard/src/data -> project root is parents[2]
    return Path(__file__).resolve().parents[2] / "phase1_outputs" / "PHASE_1_4_CALIBRATION.json"


def load_calibration_profile(path: str | Path | None = None) -> dict[str, Any]:
    profile_path = _calibration_path(path)
    if not profile_path.exists():
        raise FileNotFoundError(
            f"Phase 1.4 calibration profile not found: {profile_path}"
        )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    required = {"selected_model", "selected_features", "selected_coefficients"}
    missing = required - set(profile)
    if missing:
        raise ValueError(
            f"Calibration profile is incomplete; missing {sorted(missing)}"
        )
    if profile["selected_model"] != "distance_only":
        raise ValueError(
            "Phase 2.2 currently expects the validated Phase 1.4 distance_only model."
        )
    if profile["selected_features"] != ["distance_km"]:
        raise ValueError(
            "Calibration profile features do not match the Phase 1.4 contract."
        )
    if len(profile["selected_coefficients"]) != 2:
        raise ValueError("Expected intercept and distance coefficient.")
    return profile


def _build_demand_table(order_fact: pd.DataFrame, state_coordinates: pd.DataFrame) -> pd.DataFrame:
    demand = build_state_demand(order_fact, state_coordinates).rename(
        columns={"orders": "demand_orders", "customer_state": "state"}
    )
    total = demand["demand_orders"].sum()
    demand["demand_share_pct"] = np.where(
        total > 0,
        demand["demand_orders"] / total * 100.0,
        0.0,
    )
    return demand.sort_values("state").reset_index(drop=True)


def _build_candidate_hubs(
    seller_capacity: pd.DataFrame,
    state_coordinates: pd.DataFrame,
) -> pd.DataFrame:
    hubs = seller_capacity.rename(
        columns={
            "seller_state": "state",
            "sellers": "seller_count",
            "historical_orders": "historical_orders",
            "historical_items": "historical_items",
        }
    ).copy()
    hubs["base_capacity_orders"] = hubs["historical_orders"]
    hubs = hubs.merge(
        state_coordinates[["state", "latitude", "longitude"]],
        on="state",
        how="left",
        validate="one_to_one",
    )
    hubs = hubs.sort_values(
        ["historical_orders", "state"], ascending=[False, True]
    ).reset_index(drop=True)
    hubs["candidate_rank_by_historical_orders"] = np.arange(1, len(hubs) + 1)
    return hubs


def _build_cost_matrix(
    state_coordinates: pd.DataFrame,
    candidate_hubs: pd.DataFrame,
    demand_table: pd.DataFrame,
    calibration_profile: dict[str, Any],
) -> pd.DataFrame:
    intercept, distance_coef = map(
        float, calibration_profile["selected_coefficients"]
    )
    distances = build_state_distance_matrix(state_coordinates)
    hub_states = candidate_hubs["state"].tolist()
    demand_states = demand_table["state"].tolist()

    lane = distances[
        distances["origin_state"].isin(hub_states)
        & distances["destination_state"].isin(demand_states)
    ].copy()
    lane["calibrated_cost_per_order"] = (
        intercept + distance_coef * lane["distance_km"]
    ).clip(lower=0.0)

    matrix = lane.pivot(
        index="origin_state",
        columns="destination_state",
        values="calibrated_cost_per_order",
    ).reindex(index=hub_states, columns=demand_states)

    if matrix.isna().any().any():
        missing = matrix.isna().stack()
        missing_pairs = missing[missing].index.tolist()[:10]
        raise ValueError(
            f"Transportation cost matrix has missing lanes; examples: {missing_pairs}"
        )

    matrix.columns.name = None
    return matrix.reset_index()


def build_canonical_bundle(
    data_dir: str | Path,
    calibration_profile_path: str | Path | None = None,
) -> CanonicalDataBundle:
    """Run Phase 1.1–1.4 and return canonical dashboard inputs."""
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Olist data directory does not exist: {data_dir}")

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
    source_paths = {k: data_dir / v for k, v in filenames.items()}
    missing = [str(p) for p in source_paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing Olist files: " + ", ".join(missing))

    data = load_olist(data_dir)
    reference_checks = validate_references(data)
    if any(v != 0 for v in reference_checks.values()):
        raise ValueError(
            "Referential-integrity validation failed: "
            + "; ".join(f"{k}={v}" for k, v in reference_checks.items() if v)
        )

    order_fact = build_order_fact(data)
    zip_coordinates = build_zip_coordinates(data["geolocation"])
    state_coordinates = build_state_coordinates(data["geolocation"])
    distance_matrix_long = build_state_distance_matrix(state_coordinates)

    # Build the actual entity ZIP -> coordinate mappings so the canonical
    # bundle contains the Phase 1.2 geographic products used by the dashboard.
    customer_geo = map_zip_to_entities(
        data["customers"], "customer_zip_code_prefix", zip_coordinates
    )
    seller_geo = map_zip_to_entities(
        data["sellers"], "seller_zip_code_prefix", zip_coordinates
    )

    demand_table = _build_demand_table(order_fact, state_coordinates)
    seller_capacity = build_seller_state_capacity(data)
    candidate_hubs = _build_candidate_hubs(seller_capacity, state_coordinates)
    calibration_profile = load_calibration_profile(calibration_profile_path)
    cost_matrix = _build_cost_matrix(
        state_coordinates,
        candidate_hubs,
        demand_table,
        calibration_profile,
    )

    canonical_checks = validate_canonical_inputs(
        demand_table, candidate_hubs, cost_matrix
    )
    canonical_checks.update({
        "state_coordinates_cover_demand": bool(
            demand_table[["latitude", "longitude"]].notna().all().all()
        ),
        "candidate_hubs_have_coordinates": bool(
            candidate_hubs[["latitude", "longitude"]].notna().all().all()
        ),
        "cost_matrix_has_no_missing": bool(
            not cost_matrix.drop(columns=["origin_state"]).isna().any().any()
        ),
        "cost_matrix_nonnegative": bool(
            (cost_matrix.drop(columns=["origin_state"]) >= 0).all().all()
        ),
        "candidate_hubs_have_positive_capacity": bool(
            (candidate_hubs["base_capacity_orders"] > 0).all()
        ),
        "demand_total_positive": bool(demand_table["demand_orders"].sum() > 0),
    })

    metadata = {
        "phase1_stages": ["1.1_ingestion", "1.2_geography", "1.3_demand_capacity", "1.4_cost_calibration"],
        "demand_definition": "unique Olist orders by customer state",
        "candidate_hub_definition": "states with at least one observed Olist seller",
        "capacity_definition": "historical distinct Olist orders associated with sellers in state",
        "cost_definition": "Phase 1.4 calibrated freight cost per order",
        "customer_geo_rows": len(customer_geo),
        "seller_geo_rows": len(seller_geo),
        "demand_states": len(demand_table),
        "candidate_hubs": len(candidate_hubs),
        "cost_lanes": (len(candidate_hubs) * len(demand_table)),
        "calibration_model": calibration_profile["selected_model"],
        "calibration_coefficients": calibration_profile["selected_coefficients"],
    }

    return CanonicalDataBundle(
        raw_data=data,
        order_fact=order_fact,
        zip_coordinates=zip_coordinates,
        state_coordinates=state_coordinates,
        distance_matrix_long=distance_matrix_long,
        demand_table=demand_table,
        seller_capacity=seller_capacity,
        candidate_hubs=candidate_hubs,
        cost_matrix=cost_matrix,
        calibration_profile=calibration_profile,
        reference_checks=reference_checks,
        canonical_checks=canonical_checks,
        source_files={k: str(v) for k, v in source_paths.items()},
        dataset_fingerprint=_fingerprint_files(source_paths),
        metadata=metadata,
    )
