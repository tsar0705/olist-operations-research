"""Phase 2.3 — Upload-time validation helpers.

The Streamlit layer uses these helpers to validate uploaded Olist CSVs before
handing them to the Phase 1 service. The helpers do not contain optimization
logic and do not create synthetic fallback data.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Mapping

import pandas as pd

from .olist_preprocessing import EXPECTED_COLUMNS
from .phase1_service import build_canonical_bundle

FILE_NAMES = {
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


@dataclass(frozen=True)
class FileValidation:
    key: str
    filename: str
    uploaded: bool
    rows: int = 0
    columns: int = 0
    missing_columns: tuple[str, ...] = ()
    extra_columns: tuple[str, ...] = ()
    error: str | None = None

    @property
    def valid(self) -> bool:
        return self.uploaded and not self.missing_columns and self.error is None and self.rows > 0


def _read_uploaded_schema(uploaded_file) -> tuple[int, list[str]]:
    """Read the uploaded CSV through its byte payload.

    Streamlit's UploadedFile behaves like a file object, but using its bytes
    also keeps this helper easy to test with in-memory upload doubles.
    """
    payload = uploaded_file.getvalue()
    frame = pd.read_csv(BytesIO(payload))
    return len(frame), list(frame.columns)


def validate_uploaded_files(uploaded_files: Mapping[str, object]) -> list[FileValidation]:
    """Validate the nine logical Olist uploads against Phase 1.1 schemas."""
    results: list[FileValidation] = []
    for key, filename in FILE_NAMES.items():
        uploaded = uploaded_files.get(key)
        if uploaded is None:
            results.append(FileValidation(key, filename, False))
            continue

        try:
            rows, columns = _read_uploaded_schema(uploaded)
            expected = set(EXPECTED_COLUMNS[key])
            actual = set(columns)
            results.append(
                FileValidation(
                    key=key,
                    filename=filename,
                    uploaded=True,
                    rows=rows,
                    columns=len(columns),
                    missing_columns=tuple(sorted(expected - actual)),
                    extra_columns=tuple(sorted(actual - expected)),
                )
            )
        except Exception as exc:  # upload feedback should never crash the app
            results.append(
                FileValidation(
                    key=key,
                    filename=filename,
                    uploaded=True,
                    error=f"Could not read CSV: {exc}",
                )
            )
    return results


def all_required_files_uploaded(results: list[FileValidation]) -> bool:
    return all(item.uploaded for item in results)


def all_schemas_valid(results: list[FileValidation]) -> bool:
    return all(item.valid for item in results)


def build_bundle_from_uploads(uploaded_files: Mapping[str, object]):
    """Materialize uploads into an isolated temporary directory and run Phase 1."""
    with TemporaryDirectory(prefix="olist_dashboard_") as temp_dir:
        temp_path = Path(temp_dir)
        for key, filename in FILE_NAMES.items():
            uploaded = uploaded_files[key]
            uploaded.seek(0)
            target = temp_path / filename
            target.write_bytes(uploaded.getvalue())
            uploaded.seek(0)

        # build_canonical_bundle reads the exact Olist filenames expected by
        # the validated Phase 1 pipeline. No UI preprocessing occurs here.
        return build_canonical_bundle(temp_path)
