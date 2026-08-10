"""
Phase 1.2 — Olist geographic preprocessing.

Builds:
- ZIP-prefix centroid lookup from the actual Olist geolocation table
- customer ZIP -> coordinates mapping
- seller ZIP -> coordinates mapping
- state centroids
- state-to-state Haversine distance matrix
- seller-state/customer-state historical lane table

No transportation-rate assumption is introduced here.
"""

from pathlib import Path
import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0088

def haversine_km(lat1, lon1, lat2, lon2):
    p1 = np.radians(lat1)
    p2 = np.radians(lat2)
    dp = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))

def build_zip_coordinates(geolocation):
    geo = geolocation.drop_duplicates().copy()
    geo["geolocation_zip_code_prefix"] = pd.to_numeric(
        geo["geolocation_zip_code_prefix"], errors="coerce"
    ).astype("Int64")
    return (
        geo.groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(
            latitude=("geolocation_lat", "mean"),
            longitude=("geolocation_lng", "mean"),
            state_mode=("geolocation_state",
                        lambda s: s.mode().iat[0] if not s.mode().empty else pd.NA),
            coordinate_observations=("geolocation_lat", "size"),
        )
    )

def build_state_coordinates(geolocation):
    geo = geolocation.drop_duplicates()
    return (
        geo.groupby("geolocation_state", as_index=False)
        .agg(
            latitude=("geolocation_lat", "mean"),
            longitude=("geolocation_lng", "mean"),
            coordinate_observations=("geolocation_zip_code_prefix", "size"),
            unique_zip_prefixes=("geolocation_zip_code_prefix", "nunique"),
        )
        .rename(columns={"geolocation_state": "state"})
    )

def build_state_distance_matrix(state_coordinates):
    rows = []
    states = state_coordinates["state"].tolist()
    for origin in states:
        o = state_coordinates.loc[
            state_coordinates["state"] == origin
        ].iloc[0]
        for destination in states:
            d = state_coordinates.loc[
                state_coordinates["state"] == destination
            ].iloc[0]
            rows.append({
                "origin_state": origin,
                "destination_state": destination,
                "distance_km": float(haversine_km(
                    o["latitude"], o["longitude"],
                    d["latitude"], d["longitude"]
                )),
            })
    return pd.DataFrame(rows)

def map_zip_to_entities(entity_df, zip_col, zip_coordinates):
    return entity_df.merge(
        zip_coordinates,
        left_on=zip_col,
        right_on="geolocation_zip_code_prefix",
        how="left",
        validate="many_to_one",
    ).drop(columns=["geolocation_zip_code_prefix"])
