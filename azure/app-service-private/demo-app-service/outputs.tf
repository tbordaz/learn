output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "vm_public_ip" {
  description = "Public IP address of the demo VM."
  value       = azurerm_public_ip.vm_pip.ip_address
}

output "vm_ssh_command" {
  description = "Command to SSH into the VM."
  value       = format("ssh -i ~/.ssh/demo-vm-ssh-key %s@%s", var.vm_admin_username, azurerm_public_ip.vm_pip.ip_address)
}

output "web_app_hostname" {
  description = "Default hostname of the Web App."
  value       = azurerm_linux_web_app.webapp.default_hostname
}

output "web_app_name" {
  description = "Name of the Web App."
  value       = azurerm_linux_web_app.webapp.name
}

output "nat_gateway_public_ip" {
  description = "Public IP address used by the NAT Gateway."
  value       = azurerm_public_ip.nat_pip.ip_address
}

output "appserviceudr_id" {
  description = "ID of the App Service User Defined Route table."
  value       = azurerm_route_table.appserviceudr.id
}

output "vnet_name" {
  description = "Name of the Virtual Network."
  value       = azurerm_virtual_network.vnet.name
}