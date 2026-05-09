variable "name_prefix" {
  description = "A short, lowercase prefix that will be prepended to resource names. Storage account names must be globally unique across all of Azure, so include something distinctive (e.g. your initials)."
  type        = string
  default     = "sidshelh"  # Siddharth Shenoy + lakehouse
  validation {
    condition     = can(regex("^[a-z0-9]{4,10}$", var.name_prefix))
    error_message = "name_prefix must be 4-10 chars, lowercase letters and digits only."
  }
}

variable "location" {
  description = "Azure region where resources will be created. Pick the region closest to you for lowest latency."
  type        = string
  default     = "centralindia"
}

variable "environment" {
  description = "Environment tag (dev, staging, prod). Drives naming and resource sizing."
  type        = string
  default     = "dev"
}
