# Olist Operations Research Dashboard

A decision-support dashboard for **Operations Research-based logistics optimization**, developed using the publicly available **Brazilian E-Commerce by Olist** dataset.

The project combines real-world e-commerce data preprocessing, geographic analysis, mathematical optimization, sensitivity analysis, validation, and an interactive Streamlit dashboard.

**GitHub:** https://github.com/tsar0705/olist-operations-research

**Live Demo:** https://olist-operations-research-r5gnvwb5n5v7em9a9appuii.streamlit.app/

> **Repository description:** Operations Research decision-support dashboard for Olist e-commerce logistics, combining real-data preprocessing, geographic analysis, facility location, transportation, seller assignment, sensitivity analysis, validation, and interactive Streamlit visualizations.

---

## Project Overview

The objective of this project is to demonstrate how Operations Research techniques can be applied to a real e-commerce logistics problem.

The application provides an end-to-end workflow:

```text
Olist CSV Data
      ↓
Schema & Data Validation
      ↓
Geographic Preprocessing
      ↓
Demand & Capacity Construction
      ↓
Transportation-Cost Calibration
      ↓
Optimization Models
      ↓
Sensitivity Analysis
      ↓
Interactive Dashboard
      ↓
Results, Comparison & Downloads
```

The dashboard allows users to:

* load and validate the Olist dataset;
* generate descriptive statistics on demand;
* analyze customer and seller geography;
* construct logistics demand and capacity inputs;
* solve two different optimization models;
* perform sensitivity analysis;
* visualize optimized logistics flows;
* compare optimization strategies;
* download model outputs and results.

---

# Operations Research Models

## Model 1 — Capacitated Facility Location + Transportation

Model 1 determines:

1. which candidate distribution hubs should be opened; and
2. how much demand should be transported from each opened hub to each customer state.

### Decision variables

$$
y_i =
\begin{cases}
1, & \text{if candidate hub } i \text{ is opened},\\
0, & \text{otherwise}.
\end{cases}
$$

$$
x_{ij} \geq 0
$$

where $x_{ij}$ represents the quantity transported from hub $i$ to customer region $j$.


### Model 1 notation

| Symbol | Meaning |
|---|---|
| $i$ | Candidate hub / facility |
| $j$ | Customer demand region / state |
| $D_j$ | Demand at customer region $j$ |
| $Cap_i$ | Capacity of candidate hub $i$ |
| $F_i$ | Fixed cost of opening hub $i$ |
| $C_{ij}$ | Unit transportation cost from hub $i$ to region $j$ |
| $x_{ij}$ | Quantity shipped from hub $i$ to region $j$ |
| $y_i$ | Binary hub-opening decision |


### Objective

$$
\min
\left(
\sum_i F_i y_i
+
\sum_i \sum_j C_{ij}x_{ij}
\right)
$$

where:

* $F_i$ = fixed cost of opening hub $i$;
* $C_{ij}$ = transportation cost per unit from hub $i$ to customer region $j$;
* $x_{ij}$ = shipment quantity;
* $y_i$ = hub-opening decision.

### Main constraints

**Demand satisfaction**

$$
\sum_i x_{ij} = D_j
\qquad \forall j
$$

**Hub capacity**

$$
\sum_j x_{ij} \leq Cap_i y_i
\qquad \forall i
$$

**Hub-opening decision**

$$
y_i \in \{0,1\}
$$

**Shipment non-negativity**

$$
x_{ij} \geq 0
$$

This is a mixed-integer facility-location and transportation model.

---

# Model 2 — Seller-State Assignment

Model 2 considers a different logistics decision.

Each customer state is assigned to a single seller state while respecting seller-state fulfillment capacity.

This creates a contrast between:

| Model 1                            | Model 2                          |
| ---------------------------------- | -------------------------------- |
| Opens distribution hubs            | Uses existing seller states      |
| Allows shipment splitting          | Single-source assignment         |
| Facility-location + transportation | Assignment / integer programming |
| Infrastructure decision            | Allocation decision              |

The comparison allows the project to demonstrate two distinct optimization formulations rather than simply solving the same model twice.

---

# Sensitivity Analysis

The dashboard provides scenario analysis around the validated optimization models.

The implemented experiments include:

* facility fixed-cost sensitivity;
* hub-capacity sensitivity;
* demand-growth sensitivity;
* transportation-cost stress;
* fixed-cost × capacity scenarios;
* Model 2 capacity sensitivity;
* transportation-only capacity benchmarking.

Sensitivity analysis is used to study how changes in important parameters affect:

* total optimization cost;
* selected hubs;
* capacity utilization;
* transportation flows;
* feasibility;
* model preference.

---

# Dataset

The project uses the publicly available **Brazilian E-Commerce by Olist** dataset.

Source:

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

The nine required tables are:

```text
olist_customers_dataset.csv
olist_geolocation_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

The dataset contains approximately 100,000 orders and provides customer, seller, product, payment, review, order, and geographic information.

### Dataset handling

The raw CSV files are **not committed to this Git repository**.

This keeps the repository lightweight and reproducible while allowing the application to work with the original public dataset.

Users can either:

1. place the nine CSV files inside `data/`; or
2. specify their location using `OLIST_DATA_DIR`.

---

# Real Data Pipeline

The project **does not** use synthetic/demo data for its final analytical results.

The Phase 1 pipeline performs:

### 1. Schema validation

Validates the required Olist tables and their expected structure.

### 2. Geographic preprocessing

Processes:

* customer ZIP-code prefixes;
* seller ZIP-code prefixes;
* Olist geolocation data;
* latitude/longitude;
* state-level geographic aggregation;
* customer-to-seller/hub distance information.

### 3. Demand construction

Customer demand is aggregated at state level.

The final Olist dataset contains:

```text
Orders:          99,441
Customer states: 27
Seller states:   23
```

### 4. Seller capacity construction

Seller-state capacity is derived from the actual seller/order-item data rather than being manually entered for the final real-data pipeline.

### 5. Transportation-cost calibration

Transportation costs are calibrated using the real Olist logistics data and the project's documented assumptions.

---

# Validated Real-Olist Results

The complete Phase 1 → Phase 2 pipeline was executed against the actual Olist dataset.

### Dataset validation

| Metric               | Result |
| -------------------- | -----: |
| Orders               | 99,441 |
| Customer states      |     27 |
| Seller states        |     23 |
| Transportation lanes |    621 |

### Model 1

| Metric        |         Result |
| ------------- | -------------: |
| Objective     | R$2,254,243.14 |
| Selected hubs |     SP, MG, PR |
| Status        |        Optimal |

### Model 2

| Metric             |         Result |
| ------------------ | -------------: |
| Objective          | R$2,052,400.80 |
| Seller states used |             13 |
| Status             |        Optimal |

These values are outputs from the actual Olist preprocessing and optimization pipeline, not synthetic demonstration data.

---

# Dashboard

The application is implemented using **Streamlit**.

The main workflow is:

```text
┌───────────────────────────────────────┐
│ Upload & Validation                   │
└───────────────────┬───────────────────┘
                    ↓
┌───────────────────────────────────────┐
│ Data & Statistics                     │
└───────────────────┬───────────────────┘
                    ↓
┌───────────────────────────────────────┐
│ Model 1 — Facility Location           │
└───────────────────┬───────────────────┘
                    ↓
┌───────────────────────────────────────┐
│ Model 2 — Seller Assignment            │
└───────────────────┬───────────────────┘
                    ↓
┌───────────────────────────────────────┐
│ Sensitivity Analysis                  │
└───────────────────┬───────────────────┘
                    ↓
┌───────────────────────────────────────┐
│ Maps & Result Visualizations           │
└───────────────────┬───────────────────┘
                    ↓
┌───────────────────────────────────────┐
│ Model Comparison & Downloads           │
└───────────────────────────────────────┘
```

---

# Architecture

The application separates data engineering, optimization, analytics, validation, and presentation.

```text
                         Streamlit UI
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          Upload           Models         Analytics
             │                │                │
             ↓                ↓                ↓
       Validation       Model 1 / Model 2   Sensitivity
             │                │                │
             └────────────────┼────────────────┘
                              ↓
                    Canonical Data Bundle
                              ↑
                              │
                    Phase 1 Data Pipeline
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
    Olist Data          Geography             Calibration
```

The Streamlit application acts primarily as the presentation and orchestration layer.

The analytical responsibilities remain separated:

### Data layer

* schema validation;
* Olist preprocessing;
* geographic processing;
* demand construction;
* seller-capacity construction;
* transportation-cost calibration.

### Optimization layer

* Model 1;
* Model 2;
* optimization result contracts;
* scenario execution;
* model comparison.

### Analytics layer

* sensitivity experiments;
* scenario summaries;
* benchmark analysis.

### UI layer

* upload interface;
* statistics;
* model controls;
* maps;
* charts;
* result tables;
* downloads.

This separation prevents the dashboard from duplicating the underlying analytical logic.

---

# Project Structure

```text
olist-operations-research/
│
├── app.py
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
├── .env.example
│
├── .streamlit/
│   └── config.toml
│
├── data/
│   └── README.md
│
├── phase1_outputs/
│   └── PHASE_1_4_CALIBRATION.json
│
├── src/
│   ├── data/
│   ├── optimization/
│   ├── analytics/
│   ├── validation/
│   └── ui/
│
├── scripts/
│   ├── run_full_e2e.py
│   └── run_release_gate.py
│
└── tests/
    ├── test_live_app.py
    ├── test_olist_e2e.py
    ├── test_phase2_9.py
    ├── test_phase2_10.py
    ├── test_phase2_11.py
    └── test_phase2_12.py
```

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/tsar0705/olist-operations-research.git
cd olist-operations-research
```

## 2. Create a virtual environment

### Windows

```bat
python -m venv .venv
.venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

For development and testing:

```bash
python -m pip install -r requirements-dev.txt
```

---

# Add the Olist Dataset

Recommended structure:

```text
olist-operations-research/
│
├── data/
│   ├── olist_customers_dataset.csv
│   ├── olist_geolocation_dataset.csv
│   ├── olist_order_items_dataset.csv
│   ├── olist_order_payments_dataset.csv
│   ├── olist_order_reviews_dataset.csv
│   ├── olist_orders_dataset.csv
│   ├── olist_products_dataset.csv
│   ├── olist_sellers_dataset.csv
│   └── product_category_name_translation.csv
│
└── ...
```

Alternatively:

### Windows

```bat
set OLIST_DATA_DIR=C:\path\to\olist-data
```

### macOS/Linux

```bash
export OLIST_DATA_DIR=/path/to/olist-data
```

---

# Run the Dashboard

```bash
python -m streamlit run app.py
```

Streamlit will display the local URL in the terminal.

---

# Testing

Run the complete automated test suite:

```bash
python -m pytest -q
```

The validated project currently passes:

```text
25 passed
```

Run the complete real-Olist pipeline:

```bash
python scripts/run_full_e2e.py
```

Run the release gate:

```bash
python scripts/run_release_gate.py
```

The end-to-end test validates:

* Olist data discovery;
* canonical preprocessing;
* demand construction;
* geographic processing;
* transportation lanes;
* Model 1;
* Model 2;
* model comparison.

---

# Reproducibility

For a fresh reproduction:

```text
1. Clone repository
2. Download Olist dataset
3. Place nine CSV files in data/
4. Create virtual environment
5. Install requirements
6. Run pytest
7. Run full E2E validation
8. Launch Streamlit
```

The raw Olist dataset is intentionally excluded from GitHub.

---

# Operations Research Concepts Demonstrated

This project applies concepts from the Operations Research syllabus, including:

* Linear Programming;
* Transportation Models;
* Assignment Models;
* Integer Programming;
* Facility Location;
* Capacity-Constrained Optimization;
* Sensitivity Analysis;
* Network/Logistics Optimization;
* Scenario Analysis;
* Interpretation of Optimization Results.

The project therefore demonstrates both **mathematical formulation** and **practical decision-support implementation**.

---

# Limitations and Assumptions

Some model parameters are not directly available in the Olist dataset.

In particular, facility-related costs and capacity assumptions require explicit modelling assumptions or calibrated proxies.

These assumptions are kept separate from the raw Olist data and documented in the Phase 1 calibration outputs.

Consequently, the optimization results should be interpreted as a **decision-support model under the stated assumptions**, rather than as a reconstruction of Olist's historical logistics network.

---

# Academic Project Deliverables

The repository contains:

* source code;
* preprocessing pipeline;
* mathematical optimization models;
* validation tests;
* sensitivity analysis;
* Streamlit dashboard;
* end-to-end test runner;
* release-gate checks;
* Phase 2 development reports.

The raw dataset is distributed separately through its public source.

---

# Dataset Attribution

Brazilian E-Commerce Public Dataset by Olist:

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Please refer to the original dataset source for its applicable terms and attribution requirements.

---

# Project Status

**Phase 3.3 — Deployment & Professor Demo: complete**

Validated implementation status:

```text
Phase 1 — Data & Optimization Foundation      ✅
Phase 2 — Dashboard Development               ✅
Phase 2.11 — E2E Testing                      ✅
Phase 2.12 — UI Polish & Hardening            ✅
Phase 3.1 — GitHub-ready Package              ✅
Phase 3.2 — Final Documentation               ✅
Phase 3.3 — Deployment & Professor Demo        ✅
```

Latest validated test result:

```text
25 passed
```

---

## Repository

https://github.com/tsar0705/olist-operations-research

## Live Demo

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://olist-operations-research-r5gnvwb5n5v7em9a9appuii.streamlit.app)

**Live Dashboard:** https://olist-operations-research-r5gnvwb5n5v7em9a9appuii.streamlit.app
