# Access Control Notes

## Unity Catalog

Three schemas under one `data_platform` catalog:

- **raw** : the CSV data as-is after landing (batting, people, salaries, schools, college_playing)
- **curated** : same tables but cleaned up, typed properly, stored as Delta
- **analytics** : derived stuff like team_efficiency

Pretty standard medallion-ish layout. Didn't go with bronze/silver/gold naming because there's only three levels and the names above are more descriptive.

## Permissions

Data engineers get full access to raw and curated (they need to debug and rerun pipelines). Analysts can only query the analytics schema — no reason for them to poke around in raw data. The ETL service principal reads from raw and writes to curated, nothing else.

Admins get everything obviously.

## Secrets

Went with instance profiles here since we're all-in on AWS. The Databricks cluster assumes the IAM role from `infra/iam.tf` and picks up credentials from EC2 metadata — no secrets to rotate or store anywhere.

If we ever need non-AWS creds (Slack webhooks, third-party API keys, whatever), I'd set up a Databricks Secret Scope with per-group ACLs:
```
dbutils.secrets.get(scope="data-platform", key="slack-webhook-url")
```

Just don't put secrets in notebook code or job parameters. Seen that go wrong before.
