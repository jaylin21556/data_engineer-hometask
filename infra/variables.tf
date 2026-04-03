variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "data-platform"
}

variable "owner" {
  description = "Team or individual owning the resources"
  type        = string
  default     = "eng-data"
}

variable "cost_center" {
  description = "Cost center for billing attribution"
  type        = string
  default     = "1234"
}

variable "monthly_budget_amount" {
  description = "Monthly budget threshold in USD"
  type        = number
  default     = 500
}

variable "budget_alert_emails" {
  description = "Email addresses for budget alerts"
  type        = list(string)
  default     = ["data-team@example.com"]
}

variable "raw_lifecycle_days" {
  description = "Days before raw objects transition to IA"
  type        = number
  default     = 30
}

variable "raw_expiration_days" {
  description = "Days before raw objects are permanently deleted"
  type        = number
  default     = 90
}

variable "common_tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default     = {}
}
