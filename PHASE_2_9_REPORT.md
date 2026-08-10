# Phase 2.9 — Maps + Result Visualizations

## Objective

Replace the remaining prototype-style map logic with a centralized, validated
visualization layer that consumes the Phase 1 canonical geography and validated
optimization result objects.

The dashboard architecture requires the final map to use real Phase 1
coordinates, with Model 1 showing hub markers, demand-state markers and
shipment lines, and Model 2 showing seller-state markers, customer-state
markers and assignment lines.

## Implemented

### 1. Centralized visualization module

Added:

`src/ui/result_visualizations.py`

It contains presentation-only functions for:

- canonical demand-state map
- Model 1 network map
- Model 2 assignment map
- Model 1 hub utilization
- Model 1 top lane transportation cost
- Model 1 shadow-price diagnostics
- Model 2 seller utilization
- Model 2 top assignment cost
- consistent result-table CSV downloads

No optimization equations, geographic calculations, or hard-coded coordinates
are introduced in the UI.

### 2. Model 1 visualization

The Model 1 result page now exposes:

- opened hub markers
- customer-state demand markers
- shipment lanes
- lane width scaled by order volume
- hover details for origin, destination, orders and calibrated cost/order
- hub utilization
- top transportation-cost lanes
- shadow-price diagnostics
- decision/utilization/flow downloads

The map caps displayed lanes at the 60 largest by order volume so the map
remains legible while the full solution stays available in the table.

### 3. Model 2 visualization

The Model 2 result page now exposes:

- used seller-state markers
- customer-state markers
- single-source assignment lines
- lane width scaled by assigned demand
- hover details for assignment and calibrated cost/order
- seller-state utilization
- top assignment-cost lanes
- assignment decision/utilization downloads

### 4. Coordinate source

The visualization layer reads:

`bundle.state_coordinates`

which is produced by the Phase 1 geography service from the Olist geolocation
dataset. It does not contain a `STATE_COORDS = {...}` dictionary.

This is consistent with the Phase 2 architecture requirement that maps use
real Olist-derived coordinates and that hard-coded geographic coordinates be
removed from the dashboard.

### 5. Navigation integration

The application navigation now exposes:

- Dataset Upload & Validation
- Model 1 — Facility Location
- Model 2 — Seller Assignment
- Sensitivity Analysis
- Architecture Status

### 6. State compatibility

`AppState` now provides:

- `canonical_bundle`
- `dataset_fingerprint`
- `metadata`
- `optimization_cache`

as compatibility helpers for the Phase 2.6–2.9 UI modules.

This also fixes the mismatch between the upload page's `canonical_data` field
and the result pages' `canonical_bundle` expectation.

## Validation / robustness

The visualization layer:

- refuses to render when the result has no valid flow/assignment data;
- checks that every plotted state exists in the canonical coordinate table;
- does not silently invent missing coordinates;
- keeps the full optimization tables separate from the visually capped map;
- leaves model validation to the validated OptimizationResult contract.

## Important source-derived constraints

The Phase 2 architecture specifies:

- Model 1 map = hub markers + demand-state markers + shipment lines;
- Model 2 map = seller-state markers + customer-state markers + assignment lines;
- real Phase 1 coordinates must be used;
- no hard-coded `STATE_COORDS` dictionary is allowed;
- every displayed optimization result must pass validation.

The Phase 2.9 implementation follows those constraints.

## Tests

Phase 2.9 tests cover:

- AppState canonical-bundle compatibility;
- bounded/monotone flow-width scaling;
- absence of hard-coded coordinate dictionaries in the visualization layer.

The broader project regression suite should still be run against the complete
project tree before Phase 2.10 is accepted.

## Next

Phase 2.10 — downloads and Model 1 vs Model 2 scenario comparison.
