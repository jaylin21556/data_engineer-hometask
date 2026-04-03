# Cost Analysis

Looked at `aws_costs.csv` — it's 16 rows spanning Jan and Feb 2025. Small sample but enough to see the patterns.

## Where the money goes

EC2 on-demand is the elephant in the room at 63% of total spend. EBS and S3 are distant second and third. Everything else (CloudWatch, Lambda, KMS) is basically noise.

- EC2 on-demand (m5.large): $990
- EBS volumes/IOPS: $216
- S3 storage + requests: $144
- EC2 Spot (c5.large): $95 — already using Spot in dev, which is good
- CloudWatch: $27
- Lambda + KMS: ~$7

Total across the two months: roughly $1,565.

## Tag gaps

App and Env tags are on every row, which is nice. But Owner is missing on about 25% of rows (mostly CloudWatch and some S3 request lines) and CostCenter is missing on a few dev entries. Not terrible but it means cost attribution will have blind spots. I'd enforce tags through AWS Tag Policies and make sure Terraform's `default_tags` catches everything we provision.

## Savings ideas

### 1. Move compute to Spot (~$3.5k/yr)

On-demand EC2 is $495/mo. Spot pricing for m5.large is typically 60-70% cheaper. Using cluster pools with SPOT_WITH_FALLBACK means jobs won't fail if Spot capacity dries up — they'll just fall back to on-demand temporarily.

Rough math: $495 * 0.6 savings = ~$297/mo saved, so about $3,564/yr.

Implemented in `pipelines/pool_config.json`.

### 2. S3 lifecycle rules (~$300/yr)

Raw CSVs sit in S3 Standard but nobody touches them after ingestion. Moving them to Infrequent Access after 30 days saves about 40% on storage, and deleting at 90 days keeps things clean.

That's maybe $25/mo — not huge but it's free money and good hygiene.

Implemented in `infra/s3.tf`.

### 3. Cluster policies to kill idle compute (~$1.2k/yr)

Without autotermination, clusters just sit there burning money. The policy forces a 15 min timeout, caps workers at 8, and blocks oversized node types (no 4XL+ allowed). Also requires job clusters instead of all-purpose — people shouldn't be running interactive clusters for scheduled workloads.

Conservatively saves ~$100/mo from reduced idle time.

Implemented in `pipelines/cluster_policy.json`.

### Total: ~$5k/yr in savings

## What I implemented

Four controls backed by actual config files:

1. **Cluster policy** (`pipelines/cluster_policy.json`) — restricted node types (m5/c5/r5 up to 2xl), 15 min autotermination, required pools, max 8 workers
2. **S3 lifecycle** (`infra/s3.tf`) — raw to IA at 30 days, delete at 90. Curated bucket keeps versioning on for safety
3. **Spot pool** (`pipelines/pool_config.json`) — SPOT_WITH_FALLBACK, 10 min idle timeout
4. **AWS budget** (`infra/budgets.tf`) — alerts at 80% actual and 100% forecasted, scoped to the App tag
