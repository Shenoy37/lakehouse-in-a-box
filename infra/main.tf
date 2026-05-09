# =============================================================================
# Resource group — the logical container for all our Azure resources.
# Every Azure resource has to live in one. Think of it as a folder for billing,
# tags, and access control.
# =============================================================================
resource "azurerm_resource_group" "main" {
  name     = "${var.name_prefix}-${var.environment}-rg"
  location = var.location

  tags = {
    project     = "lakehouse-in-a-box"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# =============================================================================
# Storage account — this is ADLS Gen2.
# The magic flag is `is_hns_enabled = true`. HNS = Hierarchical Namespace.
# That single flag turns a regular blob storage account into ADLS Gen2,
# meaning you get real folders (not just key prefixes), POSIX-like ACLs,
# and atomic directory operations. Without HNS, this is just blob storage,
# and Auto Loader will be slow and your bills will be higher.
# =============================================================================
resource "azurerm_storage_account" "lake" {
  name                     = "${var.name_prefix}${var.environment}lake"  # no separators, must be 3-24 chars
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"           # Locally Redundant Storage — cheapest. Use ZRS or GRS in prod.
  is_hns_enabled           = true            # <-- this is what makes it ADLS Gen2

  # Disable public blob access at the account level.
  # We'll use Azure AD identity from Databricks instead of access keys.
  allow_nested_items_to_be_public = false

  # Enforce TLS 1.2 minimum. Free win, security best practice.
  min_tls_version = "TLS1_2"

  tags = {
    project     = "lakehouse-in-a-box"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# =============================================================================
# Containers — the top-level "buckets" inside the storage account.
# Three of them, one per stage of data:
#   raw         — landing zone where source files arrive
#   bronze      — Delta tables for the bronze layer
#   checkpoints — Auto Loader's internal state (don't delete this in prod!)
#
# We use a `for_each` instead of three separate resource blocks so they're
# defined declaratively. Adding a 4th container later is one line.
# =============================================================================
resource "azurerm_storage_container" "containers" {
  for_each = toset(["raw", "bronze", "checkpoints"])

  name                  = each.value
  storage_account_id    = azurerm_storage_account.lake.id
  container_access_type = "private"  # never public for a data lake
}
