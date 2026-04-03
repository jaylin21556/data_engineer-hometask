# Data Platform Take-Home

## Overview

This repo covers all four sections of the take-home: Terraform infra, Databricks admin, FinOps analysis, and the ETL aggregate. I didn't have access to a live AWS/Databricks environment so everything is written to validate and plan locally, the ingestion scripts can run with a local Spark install too.

## How it all fits together

Raw CSVs land in an encrypted S3 bucket, get picked up by a Databricks job cluster (Spot-backed, via instance pools), transformed into Delta tables in a curated bucket, and then the analytics layer builds aggregates on top.

## Repo layout

```
infra/          Terraform for AWS (S3, KMS, IAM, budgets, Config rules)
pipelines/      Databricks configs (cluster policy, pool, job) + PySpark scripts
sql/            SQL version of the team-year efficiency query
finops/         Cost breakdown and savings recommendations
docs/           This readme
```

I won't list every file here, the names should be self-explanatory. See `infra/ci_notes.md` for the GitHub Actions plan and `pipelines/access_control_notes.md` for Unity Catalog thoughts.

## Security

- Both S3 buckets use a KMS CMK with rotation enabled, and bucket policies reject non-TLS traffic
- Public access is blocked at the bucket level + AWS Config rules as a safety net
- IAM follows least privilege: the Databricks role can only read from landing and write to curated. The CI/CD role is scoped to the specific services it needs (no wildcard admin)
- CI authenticates via GitHub OIDC, no static keys
- For secrets, I went with instance profiles since we're on AWS. For anything non-AWS (webhooks etc), Databricks Secret Scopes would be the way to go

## Cost controls

The big wins based on the cost data:

- **Spot instances** (~$3.5k/yr savings) : pool config uses SPOT_WITH_FALLBACK so jobs don't fail if capacity is tight
- **Cluster policy** (~$1.2k/yr) : autotermination at 15 min, capped node types and worker count
- **S3 lifecycle** (~$300/yr) : raw data moves to IA after 30 days and gets deleted at 90
- **Budget alerts** : fires at 80% actual and 100% forecasted, filtered by App tag

More details in `finops/cost_analysis.md`.

## Running it

### Terraform

```bash
cd infra
terraform init
terraform validate
terraform plan -out=plan.tfplan
```

No apply needed due to there's no backend configured.

### Local Spark

```bash
pip install pyspark delta-spark

# ingest CSVs to Delta
spark-submit pipelines/ingest_baseball_data.py Platform_Engineer_Take_Home_Data/ output/curated/

# build the team efficiency aggregate
spark-submit pipelines/team_efficiency.py Platform_Engineer_Take_Home_Data/ output/team_efficiency/
```

### On Databricks

Upload CSVs to the landing bucket, import the notebooks via Repos, and create the job from `pipelines/job_config.json`. It's scheduled for 6 AM ET daily but can be triggered manually.

The SQL version (`sql/team_efficiency.sql`) works in any Spark SQL context.

## Testing

- `terraform validate` + `terraform plan` for the infra
- The ingestion script prints DQ stats (dropped nulls, out-of-range years), not fancy but it catches the obvious stuff
- For the ETL: check that row count matches distinct (teamID, yearID) in Batting, teams without salaries still show up with null payroll, and BA stays in [0, 1]

## What I'd do with more time

- Actually apply the Terraform and test end to end
- Set up Unity Catalog properly (the structure is described in `access_control_notes.md` but not provisioned)
- Switch from full overwrite to incremental MERGE by partition, overwrite is fine for this data size but won't scale
- Replace the print-based DQ with something like Great Expectations
- Add proper alerting (the job config has placeholder webhooks right now)
- Write pytest tests for the efficiency aggregate logic, especially edge cases like zero at-bats and multi-stint players
- Look into Compute Savings Plans for the steady-state prod workloads
