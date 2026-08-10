# Olist Operations Research Dashboard

A full-stack-style Streamlit decision-support dashboard built for an Operations Research course project using the publicly available **Brazilian E-Commerce by Olist** dataset.

The application loads the nine Olist CSV tables, validates the data, constructs the canonical Phase 1 analytical bundle, solves two optimization models, performs sensitivity analysis, visualizes the resulting logistics network, and provides downloadable results.

## What the project does

### Model 1 — Capacitated Facility Location + Transportation

The model decides:

- which candidate distribution hubs to open;
- how much demand to ship from each opened hub to each customer state.

Objective:

\[
\min \sum_i F_i y_i + \sum_{i,j} c_{ij}x_{ij}
\]

subject to demand satisfaction, hub capacity, hub-opening, and non-negativity/integrality constraints.

### Model 2 — Seller-State Assignment

The model assigns each customer state to a single seller state while respecting seller-state capacity.

This gives a useful OR comparison between:

- flexible multi-source hub allocation; and
- rigid single-source assignment.

### Sensitivity analysis

The dashboard supports the validated Phase 1 sensitivity experiments, including:

- facility fixed-cost sensitivity;
- capacity sensitivity;
- demand-growth sensitivity;
- transportation-cost stress;
- fixed-cost × capacity scenarios;
- Model 2 capacity sensitivity;
- transportation-only capacity benchmarking.

## Dataset

The project uses the nine Olist tables:

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

The dataset is publicly available through Kaggle:

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

**The CSV files are intentionally not included in this Git repository.**

## Project structure

```text
olist_or_dashboard/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
├── data/
│   └── README.md
├── phase1_outputs/
│   └── PHASE_1_4_CALIBRATION.json
├── src/
│   ├── data/
│   ├── optimization/
│   ├── analytics/
│   ├── validation/
│   └── ui/
├── scripts/
│   ├── run_release_gate.py
│   └── run_full_e2e.py
└── tests/
```

## Local setup

### 1. Clone

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd olist_or_dashboard
```

### 2. Create a virtual environment

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

For development/testing:

```bash
python -m pip install -r requirements-dev.txt
```

### 4. Place the Olist data

Recommended layout:

```text
olist_or_dashboard/
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
└── ...
```

Alternatively, point the E2E runner at another directory:

```bat
set OLIST_DATA_DIR=C:\path\to\olist-data
```

## Run the dashboard

```bash
python -m streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

The dashboard workflow is:

```text
Upload / Validate
       ↓
Data & Statistics
       ↓
Model 1
       ↓
Model 2
       ↓
Sensitivity Analysis
       ↓
Maps / Result Visualizations
       ↓
Model Comparison & Downloads
       ↓
Release / Architecture Status
```

## Run the tests

Full test suite:

```bash
python -m pytest -q
```

Real Olist end-to-end pipeline:

```bash
python scripts/run_full_e2e.py
```

Release gate:

```bash
python scripts/run_release_gate.py
```

## Validated Olist benchmark

The final real-data E2E run produced:

| Metric | Result |
|---|---:|
| Orders | 99,441 |
| Customer states | 27 |
| Seller states | 23 |
| Transportation lanes | 621 |
| Model 1 objective | R$2,254,243.14 |
| Model 1 hubs | SP, MG, PR |
| Model 2 objective | R$2,052,400.80 |
| Model 2 seller states used | 13 |

The benchmark values are validation outputs from the project's actual Olist preprocessing and optimization pipeline, not synthetic demo data.

## Important data/reproducibility note

Do not commit the nine Olist CSV files to GitHub.

For a clean submission/reproduction:

1. clone the repository;
2. download the Olist dataset from its public source;
3. place the nine CSV files under `data/`, or set `OLIST_DATA_DIR`;
4. run the tests;
5. launch Streamlit.

## Architecture principle

The Streamlit application is intentionally a presentation/orchestration layer.

The canonical Phase 1 preprocessing pipeline owns:

- schema validation;
- geographic preprocessing;
- demand construction;
- seller capacity construction;
- transportation-cost calibration.

The optimization layer owns the mathematical models.

The UI consumes those validated outputs rather than rebuilding analytical logic inside Streamlit.

## Academic scope

This project demonstrates concepts from the Operations Research syllabus including:

- linear programming;
- transportation models;
- assignment models;
- integer programming;
- facility location;
- sensitivity analysis;
- network/logistics optimization;
- interpretation of optimization results.

## License / dataset attribution

The application code can be used for educational purposes. The Olist dataset remains subject to its original source terms and attribution requirements.
