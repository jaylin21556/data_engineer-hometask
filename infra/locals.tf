locals {
  tags = merge(
    {
      App        = var.project_name
      Env        = var.environment
      Owner      = var.owner
      CostCenter = var.cost_center
      ManagedBy  = "terraform"
    },
    var.common_tags
  )

  landing_bucket_name = "${var.project_name}-${var.environment}-landing"
  curated_bucket_name = "${var.project_name}-${var.environment}-curated"
}
