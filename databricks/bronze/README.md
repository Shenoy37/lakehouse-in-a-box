# Bronze layer

The Bronze layer ingests raw source data into Delta tables, with **no transformation logic** beyond:
1. Schema inference and evolution (Auto Loader handles this)
2. Adding audit metadata columns

That's it. No type casts, no dedup, no business logic. Bronze is the audit log of what arrived.

## What's in here

| File | What it does |
|---|---|
| `ingest_yellow_taxi.py` | The Auto Loader job for NYC TLC yellow taxi JSON |

## How to run locally

```bash
# from repo root
pip install -e ".[dev]"   # installs PySpark + Delta Lake + dev deps
pytest tests/             # runs unit tests

# Run against fake local data (you'd need to set this up; see tests/conftest.py)
python databricks/bronze/ingest_yellow_taxi.py \
    --raw-path "file:///tmp/raw" \
    --bronze-table "spark_catalog.bronze.yellow_taxi" \
    --schema-location "/tmp/schemas/yellow_taxi" \
    --checkpoint-location "/tmp/checkpoints/yellow_taxi"
```

## How to run on Databricks

The Asset Bundle (`databricks.yml`) wires this up as a job. After running `terraform output`:

```bash
databricks bundle run bronze_yellow_taxi
```

## Auto Loader configs we set, and why

| Option | Value | Why |
|---|---|---|
| `cloudFiles.format` | `json` | TLC publishes both parquet and JSON. We use JSON to make schema evolution interesting. |
| `cloudFiles.schemaLocation` | dedicated path | Auto Loader stores inferred schema here. Keep this *outside* the checkpoint dir so you can blow one away without losing the other. |
| `cloudFiles.schemaEvolutionMode` | `addNewColumns` | New columns from source = stream fails loudly, restart picks up. **Default `none` silently drops new columns.** |
| `cloudFiles.inferColumnTypes` | `true` | Don't treat all columns as strings. Real types matter downstream. |
| `cloudFiles.allowOverwrites` | `false` | If a source file is rewritten with the same name, we ignore it. Safer default. |

## Audit columns we add

| Column | Source | Why |
|---|---|---|
| `_source_file` | `_metadata.file_path` | Lets you trace any row back to its source file |
| `_source_modified_at` | `_metadata.file_modification_time` | Useful for late-data analysis |
| `_ingested_at` | `current_timestamp()` | When the row landed in Bronze |
| `_ingest_run_id` | `uuid()` | Logical batch ID for reprocessing/rollback |

## Common gotchas

**Stream fails with "schema mismatch".** Expected behaviour with `addNewColumns`. Restart the job — it will re-infer the schema and continue.

**Stream fails with "file not found".** Usually means someone deleted a file from `raw/` after Auto Loader saw it. Set `cloudFiles.allowOverwrites = false` (we do).

**Checkpoint corruption.** If the checkpoint gets into an unrecoverable state (rare, but happens after some kinds of crashes), you can blow away the *checkpoint* directory but **never the schema location** without expecting full re-ingestion. Keep them separate (we do).
