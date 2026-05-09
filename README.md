# Lakehouse-in-a-Box

A production-grade medallion lakehouse on Azure + Databricks, built end-to-end with infrastructure as code, CI/CD, data quality checks, and lineage from day one. Public dataset, public code, runs on free tiers.

## What this project is

- Real Auto Loader ingestion with schema evolution handling, not `spark.read.parquet()` calls
- Terraform-provisioned ADLS Gen2 storage and Unity Catalog setup, not click-ops
- GitHub Actions CI that runs PySpark tests on every PR
- Databricks Asset Bundle deployment, not "I copied the notebook to prod"
- DQX data quality gates between layers
- OpenLineage tracking from Bronze through Gold
- One opinionated `pipeline.yaml` that drives the whole thing

## Architecture

```
                     ADLS Gen2 (raw zone)
                            │
                            ▼
        ┌────────────────────────────────────────┐
        │  BRONZE  (Databricks Auto Loader)      │
        │  - Schema evolution: addNewColumns     │
        │  - _rescued_data captures malformed    │
        │  - One Delta table per source          │
        └─────────────────┬──────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────┐
        │  SILVER  (PySpark + DQX)               │
        │  - Conform types, drop duplicates      │
        │  - Quality gates fail the job fast     │
        │  - Slowly-changing-dimensions handling │
        └─────────────────┬──────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────┐
        │  GOLD  (dbt-databricks)                │
        │  - Star schema: fact_trips +           │
        │    dim_zone, dim_date, dim_vendor      │
        │  - Materialised as Delta tables        │
        └────────────────────────────────────────┘
```

## What's in this repo

| Folder | What lives here |
|---|---|
| `infra/` | Terraform — provisions ADLS Gen2, containers, RBAC |
| `databricks/bronze/` | Auto Loader ingestion scripts |
| `databricks/silver/` | PySpark transforms + DQX checks |
| `databricks/gold/` | (stub — built month 3) |
| `dbt/` | (stub — built month 3) |
| `tests/` | PySpark unit tests |
| `.github/workflows/` | CI — lint and test on every PR |
| `databricks.yml` | Asset Bundle config for deploys |
| `pipeline.yaml` | The single source of truth for sources, sinks, transforms |

## Quickstart

```bash
# 1. Provision infra
cd infra && terraform init && terraform apply

# 2. Deploy the bundle to your Databricks workspace
databricks bundle deploy --target dev

# 3. Trigger the Bronze ingestion
databricks bundle run bronze_yellow_taxi
```

Full setup (including how to get free Azure + Databricks accounts) is in [`docs/SETUP.md`](docs/SETUP.md).

## Design decisions and tradeoffs

This section is where I explain why I made the calls I did.

**Why Delta over Iceberg.** Both work. Delta has tighter Databricks integration and Unity Catalog handles it natively. Iceberg's catalog story is still maturing on Azure. For an Azure + Databricks-first project, Delta is the pragmatic choice. Switching to Iceberg later is one config change away — no schema migration.

**Why Auto Loader over `spark.readStream` directly.** Auto Loader handles file discovery efficiently at scale — it uses Azure Event Grid notifications instead of listing the directory on every micro-batch. For 100 files this doesn't matter. For 10 million files, it's the difference between a 30-second batch and a 30-minute one. Building with Auto Loader from the start means I don't have to migrate later.

**Why dbt for Gold but not Silver.** Silver involves complex PySpark logic (window functions over event streams, custom UDFs, conditional joins) that dbt's SQL-only model handles awkwardly. Gold is dimensional modelling — pure SQL, exactly dbt's sweet spot. Using each tool where it fits is more honest than picking one and forcing it everywhere.

**Why not DLT for everything.** Delta Live Tables is great but locks you into Databricks. The current setup runs on plain Databricks Jobs and would port to OSS Spark with minimal changes. I'll add a DLT variant in month 4 as a comparison.

**What I'd change with infinite time.** Streaming ingestion (currently triggered batches every 15 min). Real schema registry instead of inline schemas. A proper lineage UI on top of OpenLineage. dbt tests on Silver, not just Gold.

## Build progress (live)

- [x] Week 1: Skeleton + Terraform + Bronze ingestion + tests
- [] Week 2: GitHub Actions CI + Asset Bundle deploy
- [ ] Week 3: Silver layer + DQX checks
- [ ] Week 4: Gold layer + dbt + first end-to-end run
- [ ] Month 2: DLT variant + observability + OpenLineage
- [ ] Month 3: Pipeline-builder agent that scaffolds new projects from `pipeline.yaml`

## Articles I've written about this build

- (Coming soon) Bronze layer Medium piece
- (Coming soon) "What Auto Loader tutorials don't tell you"

## License

MIT. Take it, fork it, learn from it. If you do, send me a note — I'd love to know.
