variable "location" {
  description = "Azure region where resources will be deployed."
  type        = string
  default     = "southeastasia"
}

variable "base_name" {
  description = "Base name for resources to ensure uniqueness."
  type        = string
  default     = "pedemo"
}

variable "vm_admin_username" {
  description = "Admin username for the Linux VM."
  type        = string
  default     = "azureuser"
}

variable "vm_admin_ssh_key_path" {
  description = "Path to the public SSH key file for VM authentication."
  type        = string
}