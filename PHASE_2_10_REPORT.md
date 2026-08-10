# Phase 2.10 — Downloads + Model Comparison

## Objective

Add a dedicated comparison/export surface for the two validated optimization
models. The comparison must distinguish common transportation metrics from the
models' different objective structures.

## Implemented

### 1. Comparison engine

Added `src/optimization/comparison.py`.

It compares only optimal, validation-passed `OptimizationResult` objects and
reports:

- total objective;
- Model 1 fixed cost;
- transportation cost for both models;
- transportation cost per order;
- transportation-cost delta;
- hub/seller-state count;
- maximum and mean utilization;
- number of Model 1 customer states split across multiple hubs;
- Model 2 single-source structure;
- scenario compatibility on common capacity, demand and transportation multipliers.

### 2. Structural comparison

The UI explicitly documents the source-defined formulation differences:

- Model 1 opens/closes candidate hubs;
- Model 1 may split a customer state's demand;
- Model 2 single-sources each customer state;
- Model 1 includes fixed facility-opening cost;
- Model 2 is transportation-only.

This prevents an invalid interpretation where the two objective values are
reported as though they were identical cost functions.

### 3. Downloads

Added `src/ui/comparison_page.py` with:

- comparison CSV;
- structural-comparison CSV;
- individual Model 1 decision/utilization/flow CSVs;
- individual Model 2 decision/utilization/flow CSVs;
- one complete ZIP containing all result tables plus run metadata.

### 4. Navigation

Added:

`Model Comparison & Downloads`

to the main Streamlit navigation.

The page does not solve either model. It consumes the already validated results
stored in `AppState`.

## Validation

The comparison page blocks display/export when either result is not both optimal
and validation-passed.

Scenario compatibility is shown as a warning when the common scenario inputs do
not match.

## Tests

Added `tests/test_phase2_10.py` covering:

- comparison metric construction;
- Model 1 split-flow detection;
- scenario mismatch detection;
- structural comparison dimensions.

The complete project regression suite should be run in the full application
environment before Phase 2.10 is accepted.

## Next

Phase 2.11 — end-to-end dashboard tests and final integration hardening.
