# KMS key for encrypting both S3 buckets

data "aws_caller_identity" "current" {}

resource "aws_kms_key" "s3" {
  description             = "CMK for ${var.project_name} S3 bucket encryption"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # root account needs full access or you can lock yourself out
      {
        Sid    = "AllowRootAccount"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      # databricks only gets encrypt/decrypt — nothing else
      {
        Sid    = "AllowDatabricksRole"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.databricks_job.arn
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      # CI needs a bit more for terraform
      {
        Sid    = "AllowCICDRole"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.cicd.arn
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey",
          "kms:CreateGrant",
          "kms:ListGrants"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${var.project_name}-${var.environment}-s3"
  target_key_id = aws_kms_key.s3.key_id
}
