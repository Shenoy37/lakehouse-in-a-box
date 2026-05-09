"""
Unit tests for the bronze ingestion logic.

These tests use a local SparkSession (no cluster needed). They run on every
PR via GitHub Actions. The point is fast feedback — these should run in <30 sec.
"""

from __future__ import annotations
import pytest
from pyspark.sql import SparkSession

# Import the function under test. Note: we import a single function, not the
# whole script. This is why we kept add_audit_columns separate from main().
from databricks.bronze.ingest_yellow_taxi import add_audit_columns


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    """A local SparkSession for tests. Reused across all tests in the session."""
    return (
        SparkSession.builder
        .master("local[2]")
        .appName("bronze-tests")
        .config("spark.sql.shuffle.partitions", "2")  # keep tests fast
        .getOrCreate()
    )


def test_add_audit_columns_adds_four_columns(spark):
    """
    Given a DataFrame with two business columns,
    when add_audit_columns is called,
    we expect the four audit columns to be added without removing the originals.
    """
    # Arrange — a fake input DataFrame
    df = spark.createDataFrame(
        [(1, "yellow"), (2, "green")],
        schema="trip_id INT, color STRING",
    )

    # Act
    result = add_audit_columns(df)

    # Assert — original columns survived, audit columns appeared
    cols = set(result.columns)
    assert "trip_id" in cols
    assert "color" in cols
    assert "_source_file" in cols
    assert "_source_modified_at" in cols
    assert "_ingested_at" in cols
    assert "_ingest_run_id" in cols
