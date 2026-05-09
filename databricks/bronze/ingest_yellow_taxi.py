"""
Bronze ingestion: NYC TLC Yellow Taxi data.

Reads JSON files dropped into the `raw/` container by an upstream loader,
writes them as a Delta table in the `bronze/` container.

Designed to run as a Databricks Job. To run locally, you need:
  - PySpark 3.5+
  - Delta Lake 3.x
  - Azure storage credentials in env vars

Why this script is structured the way it is — read README.md in this folder.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

# -----------------------------------------------------------------------------
# Logging — we use the standard library logger so logs end up in the
# Databricks driver log automatically.
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bronze.yellow_taxi")


# -----------------------------------------------------------------------------
# Config — all the knobs in one place. In a real project this would come from
# pipeline.yaml, but we hard-code defaults here and let CLI args override.
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class Config:
    raw_path: str             # where source JSON files land
    bronze_table: str         # Delta table name (catalog.schema.table)
    schema_location: str      # where Auto Loader remembers the inferred schema
    checkpoint_location: str  # where Auto Loader remembers which files it's processed
    trigger_mode: str = "availableNow"  # "availableNow" = batch-style, "processingTime=15 minutes" = micro-batch


def parse_args() -> Config:
    """Parse CLI arguments into a Config object."""
    p = argparse.ArgumentParser()
    p.add_argument("--raw-path", required=True,
                   help="abfss:// URL where raw JSON files land")
    p.add_argument("--bronze-table", required=True,
                   help="Three-part Delta table name, e.g. main.bronze.yellow_taxi")
    p.add_argument("--schema-location", required=True,
                   help="abfss:// URL for Auto Loader's schema state")
    p.add_argument("--checkpoint-location", required=True,
                   help="abfss:// URL for Auto Loader's processed-files state")
    p.add_argument("--trigger", default="availableNow",
                   help='"availableNow" (default) or "processingTime=15 minutes"')
    args = p.parse_args()
    return Config(
        raw_path=args.raw_path,
        bronze_table=args.bronze_table,
        schema_location=args.schema_location,
        checkpoint_location=args.checkpoint_location,
        trigger_mode=args.trigger,
    )


# -----------------------------------------------------------------------------
# The actual ingestion. This is the only function that reads/writes data.
# Keeping it separate from the orchestration makes it testable.
# -----------------------------------------------------------------------------
def read_raw(spark: SparkSession, cfg: Config) -> DataFrame:
    """
    Read raw JSON with Auto Loader.

    Three configs you have to get right:
    - cloudFiles.format = json
    - cloudFiles.schemaLocation = a path Auto Loader can persist schema to
    - cloudFiles.schemaEvolutionMode = "addNewColumns"
        => when a new field appears in source, the stream fails fast (visible),
           the next run picks up the new column. This is the safe default.
           "none" = silent data loss. Don't use it.
    """
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", cfg.schema_location)
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.allowOverwrites", "false")  # never re-process the same file
        .load(cfg.raw_path)
    )


def add_audit_columns(df: DataFrame) -> DataFrame:
    """
    Add metadata columns that make Bronze auditable.

    Every Bronze row must answer "where did this come from and when did it arrive?".
    These four columns answer that. They cost almost nothing and pay off on every
    incident review.
    """
    return (
        df
        # The full source file path. Lets you tie a row back to its origin file.
        .withColumn("_source_file", F.col("_metadata.file_path"))
        # File modification time on the source. Useful for late-arriving data analysis.
        .withColumn("_source_modified_at", F.col("_metadata.file_modification_time"))
        # When this row was ingested into Bronze. Different from source time.
        .withColumn("_ingested_at", F.current_timestamp())
        # A logical ingestion-batch ID — useful for reprocessing and rollback.
        .withColumn("_ingest_run_id", F.lit(F.uuid()))
    )


def write_bronze(df: DataFrame, cfg: Config) -> None:
    """
    Write the streaming DataFrame to a Delta table.

    `mergeSchema` is set to true here so that when Auto Loader picks up new
    columns (because of `addNewColumns` evolution mode), the Delta table
    grows its schema automatically. Without `mergeSchema`, the write would fail.
    """
    log.info("Writing bronze: %s -> %s", cfg.raw_path, cfg.bronze_table)
    query = (
        df.writeStream
        .format("delta")
        .outputMode("append")
        .option("checkpointLocation", cfg.checkpoint_location)
        .option("mergeSchema", "true")
        .trigger(availableNow=True) if cfg.trigger_mode == "availableNow"
        else df.writeStream
        .format("delta")
        .outputMode("append")
        .option("checkpointLocation", cfg.checkpoint_location)
        .option("mergeSchema", "true")
        .trigger(processingTime=cfg.trigger_mode.split("=")[1].strip())
    )
    # Note: the if/else above is awkward. We'll clean it up in a refactor.
    query = query.toTable(cfg.bronze_table)
    query.awaitTermination()
    log.info("Bronze write complete.")


# -----------------------------------------------------------------------------
# Entry point.
# -----------------------------------------------------------------------------
def main() -> int:
    cfg = parse_args()
    log.info("Bronze ingestion config: %s", cfg)

    spark = (
        SparkSession.builder
        .appName("bronze.yellow_taxi")
        .getOrCreate()
    )

    raw = read_raw(spark, cfg)
    enriched = add_audit_columns(raw)
    write_bronze(enriched, cfg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
