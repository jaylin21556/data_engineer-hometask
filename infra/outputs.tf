output "landing_bucket_name" {
  description = "S3 bucket for raw CSV landing zone"
  value       = aws_s3_bucket.landing.id
}

output "curated_bucket_name" {
  description = "S3 bucket for processed Delta/Parquet data"
  value       = aws_s3_bucket.curated.id
}

output "kms_key_arn" {
  description = "KMS CMK ARN used for S3 encryption"
  value       = aws_kms_key.s3.arn
}

output "databricks_job_role_arn" {
  description = "IAM role ARN for Databricks job execution"
  value       = aws_iam_role.databricks_job.arn
}

output "cicd_role_arn" {
  description = "IAM role ARN for CI/CD pipeline"
  value       = aws_iam_role.cicd.arn
}
