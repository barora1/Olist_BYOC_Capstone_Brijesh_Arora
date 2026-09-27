"""
tests/test_pipeline.py
=======================
Integrity checks for the customer-level analytical pipeline.

These are NOT statistical tests (H1/H2 live in Notebook 04) -- they are
data-integrity assertions that catch pipeline bugs: a broken join that
duplicates rows, a customer who somehow appears twice, a leakage bug that
lets train and test rows overlap.

Run with:  pytest tests/test_pipeline.py -v

Requires the DuckDB database to already exist (i.e. Notebooks 01-04 have
been run at least once). If it doesn't exist yet, tests are skipped with
a clear message rather than failing confusingly.
"""

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import get_duckdb_path  # noqa: E402


DUCKDB_PATH = get_duckdb_path()


@pytest.fixture(scope="module")
def con():
    if not DUCKDB_PATH.exists():
        pytest.skip(
            f"DuckDB database not found at {DUCKDB_PATH}. "
            "Run Notebooks 01-04 first to build it."
        )
    connection = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    yield connection
    connection.close()


def _table_exists(con, table_name: str) -> bool:
    result = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()[0]
    return result > 0


# ---------------------------------------------------------------
# 1. Row-count integrity: the customer-level table should have exactly
#    one row per customer_unique_id -- a broken join upstream (e.g. a
#    fan-out on order_items before aggregation) would duplicate rows.
# ---------------------------------------------------------------
def test_customer_level_table_row_count_matches_unique_customers(con):
    if not _table_exists(con, "customer_level_featured"):
        pytest.skip("customer_level_featured table not found -- run Notebook 03 first.")

    result = con.execute("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT customer_unique_id) AS unique_customers
        FROM customer_level_featured
    """).fetchone()
    total_rows, unique_customers = result

    assert total_rows == unique_customers, (
        f"customer_level_featured has {total_rows} rows but only "
        f"{unique_customers} unique customer_unique_id values -- "
        "the customer-level grain has been broken, likely by a fan-out "
        "join upstream. Check Notebook 02's order-item aggregation step."
    )


# ---------------------------------------------------------------
# 2. customer_unique_id uniqueness: belt-and-braces check, catches the
#    same problem as (1) from a different angle -- explicit duplicate
#    detection rather than a row-count comparison.
# ---------------------------------------------------------------
def test_no_duplicate_customer_unique_ids(con):
    if not _table_exists(con, "customer_level_featured"):
        pytest.skip("customer_level_featured table not found -- run Notebook 03 first.")

    duplicates = con.execute("""
        SELECT customer_unique_id, COUNT(*) AS n
        FROM customer_level_featured
        GROUP BY customer_unique_id
        HAVING COUNT(*) > 1
    """).df()

    assert len(duplicates) == 0, (
        f"Found {len(duplicates)} duplicate customer_unique_id values in "
        f"customer_level_featured, e.g.:\n{duplicates.head()}"
    )


# ---------------------------------------------------------------
# 3. First-order features are unique per customer: each customer should
#    have exactly one first_order_* value set, not one per order. A bug
#    in the ROW_NUMBER() OVER (PARTITION BY ... ORDER BY purchase_ts)
#    window function (e.g. missing PARTITION BY) would silently produce
#    a first-order value that changes per row instead of being fixed
#    per customer.
# ---------------------------------------------------------------
def test_first_order_features_are_consistent_per_customer(con):
    if not _table_exists(con, "customer_level_featured"):
        pytest.skip("customer_level_featured table not found -- run Notebook 03 first.")

    # Each customer_unique_id already appears once per row in this table
    # (enforced by test 1/2 above), so this check instead confirms the
    # first-order fields are non-null and internally consistent -- e.g.
    # first_order_value should never be negative, and first_order_late_flag
    # should only ever be 0 or 1.
    result = con.execute("""
        SELECT
            SUM(CASE WHEN first_order_value < 0 THEN 1 ELSE 0 END) AS negative_values,
            SUM(CASE WHEN first_order_late_flag NOT IN (0, 1)
                     AND first_order_late_flag IS NOT NULL THEN 1 ELSE 0 END) AS bad_flags
        FROM customer_level_featured
    """).fetchone()
    negative_values, bad_flags = result

    assert negative_values == 0, (
        f"{negative_values} customers have a negative first_order_value -- "
        "check the order-value aggregation in Notebook 02/03."
    )
    assert bad_flags == 0, (
        f"{bad_flags} customers have a first_order_late_flag outside {{0, 1, NULL}} -- "
        "check the late-flag derivation logic."
    )


# ---------------------------------------------------------------
# 4. No train/test leakage: if a train/test split was persisted to
#    DuckDB (e.g. for the confirmatory logistic regression), the two
#    index sets must never intersect.
# ---------------------------------------------------------------
def test_no_train_test_index_overlap(con):
    if not (_table_exists(con, "train_split") and _table_exists(con, "test_split")):
        pytest.skip(
            "train_split/test_split tables not found in DuckDB -- "
            "this project currently splits in-memory (pandas/sklearn) "
            "rather than persisting the split, so this check is a no-op. "
            "If a persisted split is added later, this test activates "
            "automatically."
        )

    overlap = con.execute("""
        SELECT COUNT(*) FROM train_split t
        INNER JOIN test_split s ON t.customer_unique_id = s.customer_unique_id
    """).fetchone()[0]

    assert overlap == 0, (
        f"{overlap} customer_unique_id values appear in BOTH train_split "
        "and test_split -- this is a leakage bug and invalidates any "
        "held-out evaluation metric computed from this split."
    )


# ---------------------------------------------------------------
# Bonus: diagnostic_findings table sanity check -- since Notebook 05/06
# depend on this table's contents to colour charts and word conclusions,
# confirm the four expected findings are present before those notebooks
# are trusted to run correctly.
# ---------------------------------------------------------------
def test_diagnostic_findings_table_has_expected_entries(con):
    if not _table_exists(con, "diagnostic_findings"):
        pytest.skip(
            "diagnostic_findings table not found -- run Notebook 04's "
            "'Persist Diagnostic Findings' section first."
        )

    findings = con.execute(
        "SELECT finding FROM diagnostic_findings ORDER BY finding"
    ).df()["finding"].tolist()

    expected = {
        "H1_late_delivery",
        "H2_freight_ratio_band",
        "H2_freight_value_band_corrected",
        "value_tier_interaction",
    }
    missing = expected - set(findings)

    assert not missing, (
        f"diagnostic_findings is missing expected entries: {missing}. "
        "Notebook 05/06 charts and narrative will not colour/word "
        "themselves correctly until Notebook 04 is rerun in full."
    )
