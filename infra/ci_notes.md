# CI/CD Notes

I'd use GitHub Actions with a matrix strategy to handle dev and prod from a single workflow. Here's the rough shape:

```yaml
# .github/workflows/terraform.yml
name: Terraform
on:
  pull_request:
    paths: ['infra/**']
  push:
    branches: [main]
    paths: ['infra/**']

jobs:
  plan:
    strategy:
      matrix:
        environment: [dev, prod]
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init -backend-config="key=infra/${{ matrix.environment }}/terraform.tfstate"
      - run: terraform workspace select ${{ matrix.environment }} || terraform workspace new ${{ matrix.environment }}
      - run: terraform plan -var-file="envs/${{ matrix.environment }}.tfvars" -out=plan.tfplan
      - uses: actions/upload-artifact@v4
        with:
          name: plan-${{ matrix.environment }}
          path: plan.tfplan

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main'
    environment: ${{ matrix.environment }}
    strategy:
      matrix:
        environment: [dev, prod]
    steps:
      - uses: actions/download-artifact@v4
      - run: terraform apply plan.tfplan
```

## Why this setup

- **OIDC instead of static keys** : the CI role uses GitHub's OIDC provider to assume the AWS role, so there are no long-lived credentials stored as secrets. Much cleaner from a security standpoint.
- **Scoped IAM** : the cicd role in `iam.tf` can only touch S3, KMS, IAM roles, Budgets, and Config within our project namespace. No admin wildcards.
- **Plan as artifact** : the plan output gets saved so the apply step runs exactly what was reviewed. No surprises between plan and apply.
- **Manual approval for prod** : the `environment` key on the apply job hooks into GitHub Environments, so prod deploys need someone to click approve. Dev can auto-apply on merge.
- **One pipeline, multiple envs** : matrix handles both environments so there's no config drift between separate workflow files.
