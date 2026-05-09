output "storage_account_name" {
  description = "Name of the ADLS Gen2 storage account. You'll need this in Databricks to mount the lake."
  value       = azurerm_storage_account.lake.name
}

output "raw_container_url" {
  description = "abfss:// URL for the raw container. This is what Auto Loader reads from."
  value       = "abfss://raw@${azurerm_storage_account.lake.name}.dfs.core.windows.net"
}

output "bronze_container_url" {
  description = "abfss:// URL for the bronze container. Delta tables get written here."
  value       = "abfss://bronze@${azurerm_storage_account.lake.name}.dfs.core.windows.net"
}

output "checkpoints_container_url" {
  description = "abfss:// URL for Auto Loader checkpoint state. Never delete this in prod."
  value       = "abfss://checkpoints@${azurerm_storage_account.lake.name}.dfs.core.windows.net"
}

output "resource_group_name" {
  description = "Resource group name."
  value       = azurerm_resource_group.main.name
}
