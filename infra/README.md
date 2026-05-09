# Infrastructure — Terraform

This folder provisions the Azure side of the lakehouse: resource group, ADLS Gen2 storage account, and three containers (raw, bronze, checkpoints).

## Prerequisites

1. **Azure CLI** installed and logged in: `az login`
2. **Terraform** 1.6+ installed
3. An Azure subscription. The free tier is enough for this project.

## First-time setup

```bash
# 1. Set your unique name prefix. Storage account names must be globally unique.
#    Edit variables.tf and change `default = "sidshelh"` to your initials + something distinctive.

# 2. Initialize Terraform — downloads the Azure provider
terraform init

# 3. See what will be created (no changes yet)
terraform plan

# 4. Actually create the resources (~90 seconds)
terraform apply
# Type 'yes' when prompted

# 5. Read the outputs you'll need in Databricks
terraform output
```

## What gets created

| Resource | Approximate cost (free tier) | Purpose |
|---|---|---|
| Resource group | ₹0 (free) | Logical container |
| Storage account (Standard, LRS, HNS on) | ₹0 for first 5 GB / 12 months | The lake itself |
| 3 containers | ₹0 (containers are free) | raw, bronze, checkpoints |

After 12 months or above 5 GB, costs are still tiny — expect ₹50-150/month for portfolio-scale data.

## Tearing it down

When you're done experimenting (or want to reset):

```bash
terraform destroy
```

This deletes everything in this Terraform state, including any data in the containers. Don't run it casually.

## Common gotchas

**Storage account name already taken.** Storage account names are globally unique across all of Azure. If `sidshelhdevlake` is taken, change `name_prefix` in `variables.tf` to something more specific (e.g. add your birth year).

**`is_hns_enabled` cannot be changed.** If you accidentally created the storage account without HNS, you can't toggle it on. You have to destroy it and recreate. This is why we set it correctly in code from day one.

**`terraform apply` hangs on storage account creation.** This is normal. Storage accounts take 60-90 seconds to provision. Be patient.
