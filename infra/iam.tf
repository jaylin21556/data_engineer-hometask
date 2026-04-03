# Databricks job role — can read from landing and write to curated

resource "aws_iam_role" "databricks_job" {
  name = "${var.project_name}-${var.environment}-databricks-job"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::414351767826:root" # Databricks AWS account
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.project_name
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "databricks_job_s3" {
  name = "s3-data-access"
  role = aws_iam_role.databricks_job.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # read from landing
      {
        Sid    = "ReadLanding"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.landing.arn,
          "${aws_s3_bucket.landing.arn}/*"
        ]
      },
      # read+write on curated (needs delete too for Delta overwrites)
      {
        Sid    = "WriteCurated"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.curated.arn,
          "${aws_s3_bucket.curated.arn}/*"
        ]
      },
      # needs KMS to read/write encrypted objects
      {
        Sid    = "UseKMS"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = [aws_kms_key.s3.arn]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "databricks_job" {
  name = "${var.project_name}-${var.environment}-databricks-job"
  role = aws_iam_role.databricks_job.name
}

# CI/CD role for terraform — scoped to what it actually need, no admin wildcard

resource "aws_iam_role" "cicd" {
  name = "${var.project_name}-${var.environment}-cicd"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          # using GitHub OIDC so we don't need static AWS keys
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:myorg/data-platform:*"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "cicd_terraform" {
  name = "terraform-plan-apply"
  role = aws_iam_role.cicd.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Management"
        Effect = "Allow"
        Action = [
          "s3:CreateBucket",
          "s3:DeleteBucket",
          "s3:PutBucketPolicy",
          "s3:GetBucketPolicy",
          "s3:PutBucketVersioning",
          "s3:GetBucketVersioning",
          "s3:PutEncryptionConfiguration",
          "s3:GetEncryptionConfiguration",
          "s3:PutLifecycleConfiguration",
          "s3:GetLifecycleConfiguration",
          "s3:PutBucketPublicAccessBlock",
          "s3:GetBucketPublicAccessBlock",
          "s3:ListBucket",
          "s3:GetBucketTagging",
          "s3:PutBucketTagging"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-${var.environment}-*"
      },
      {
        Sid    = "KMSManagement"
        Effect = "Allow"
        Action = [
          "kms:CreateKey",
          "kms:DescribeKey",
          "kms:GetKeyPolicy",
          "kms:PutKeyPolicy",
          "kms:EnableKeyRotation",
          "kms:CreateAlias",
          "kms:DeleteAlias",
          "kms:ListAliases",
          "kms:TagResource"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/App" = var.project_name
          }
        }
      },
      {
        Sid    = "IAMManagement"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:PutRolePolicy",
          "iam:GetRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:CreateInstanceProfile",
          "iam:DeleteInstanceProfile",
          "iam:AddRoleToInstanceProfile",
          "iam:RemoveRoleFromInstanceProfile",
          "iam:PassRole",
          "iam:TagRole"
        ]
        Resource = "arn:aws:iam::*:role/${var.project_name}-${var.environment}-*"
      },
      {
        Sid    = "BudgetManagement"
        Effect = "Allow"
        Action = [
          "budgets:CreateBudget",
          "budgets:ModifyBudget",
          "budgets:ViewBudget",
          "budgets:DeleteBudget"
        ]
        Resource = "*"
      },
      {
        Sid    = "ConfigManagement"
        Effect = "Allow"
        Action = [
          "config:PutConfigRule",
          "config:DeleteConfigRule",
          "config:DescribeConfigRules"
        ]
        Resource = "*"
      }
    ]
  })
}
