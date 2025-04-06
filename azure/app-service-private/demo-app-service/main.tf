resource "random_string" "unique" {
  length  = 6
  special = false
  upper   = false
}

locals {
  resource_group_name = "rg-${var.base_name}"
  vnet_name           = "${var.base_name}-vnet"
  vm_subnet_name      = "snet-vm"
  app_int_subnet_name = "snet-appintegration"
  nsg_name            = "${var.base_name}-vm-nsg"
  vm_pip_name         = "${var.base_name}-vm-pip"
  vm_nic_name         = "${var.base_name}-vm-nic"
  vm_name             = "${var.base_name}-vm"
  app_plan_name       = "${var.base_name}-plan"
  webapp_name         = "${var.base_name}-webapp-${random_string.unique.result}"
  nat_gateway_name    = "${var.base_name}-nat-gateway"
  nat_gateway_pip_name = "${var.base_name}-nat-pip"
  udr_name            = "${var.base_name}-appserviceudr"
}

resource "azurerm_resource_group" "rg" {
  name     = local.resource_group_name
  location = var.location
}

resource "azurerm_virtual_network" "vnet" {
  name                = local.vnet_name
  address_space       = ["10.1.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "vm_subnet" {
  name                 = local.vm_subnet_name
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.1.1.0/24"]
}

resource "azurerm_subnet" "app_integration_subnet" {
  name                 = local.app_int_subnet_name
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.1.2.0/24"]
  # Delegation required for VNet integration later
  delegation {
    name = "webappdelegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Create a route table with specified routes
resource "azurerm_route_table" "appserviceudr" {
  name                = local.udr_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  # Route for internal traffic
  route {
    name                   = "internal"
    address_prefix         = "10.1.0.0/16"
    next_hop_type          = "VnetLocal"
  }

  # Route for internet traffic
  route {
    name                   = "internet"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = "10.1.1.1"
  }
}

# New Public IP for NAT Gateway
resource "azurerm_public_ip" "nat_pip" {
  name                = local.nat_gateway_pip_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"  # Standard SKU is required for NAT Gateway
}

# New NAT Gateway resource
resource "azurerm_nat_gateway" "nat_gateway" {
  name                    = local.nat_gateway_name
  location                = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  sku_name                = "Standard"  # Using Standard SKU (cheapest available for NAT Gateway)
  idle_timeout_in_minutes = 10
}

# Associate the public IP with the NAT Gateway
resource "azurerm_nat_gateway_public_ip_association" "nat_pip_assoc" {
  nat_gateway_id       = azurerm_nat_gateway.nat_gateway.id
  public_ip_address_id = azurerm_public_ip.nat_pip.id
}

# Associate ONLY the App Integration subnet with the NAT Gateway
# resource "azurerm_subnet_nat_gateway_association" "app_subnet_nat_assoc" {
#   subnet_id      = azurerm_subnet.app_integration_subnet.id
#   nat_gateway_id = azurerm_nat_gateway.nat_gateway.id
# }

resource "azurerm_network_security_group" "vm_nsg" {
  name                = local.nsg_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "AllowSSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*" # WARNING: Open to the world for demo. Restrict if needed.
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "vm_nsg_assoc" {
  subnet_id                 = azurerm_subnet.vm_subnet.id
  network_security_group_id = azurerm_network_security_group.vm_nsg.id
}

# Reverted back to Basic SKU for VM Public IP
resource "azurerm_public_ip" "vm_pip" {
  name                = local.vm_pip_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Basic"   # Basic SKU for demo VM
}

resource "azurerm_network_interface" "vm_nic" {
  name                = local.vm_nic_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.vm_subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.vm_pip.id
  }
}

resource "azurerm_linux_virtual_machine" "vm" {
  name                            = local.vm_name
  location                        = azurerm_resource_group.rg.location
  resource_group_name             = azurerm_resource_group.rg.name
  size                            = "Standard_B1s" # Smallest, cheapest burstable
  admin_username                  = var.vm_admin_username
  network_interface_ids           = [azurerm_network_interface.vm_nic.id]
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.vm_admin_username
    public_key = file(var.vm_admin_ssh_key_path)
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS" # Use Standard HDD (cheaper)
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy" # Ubuntu 22.04 LTS
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }
}

resource "azurerm_service_plan" "app_plan" {
  name                = local.app_plan_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "B1" # Basic tier required for PE/VNet Int
}

resource "azurerm_linux_web_app" "webapp" {
  name                = local.webapp_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_service_plan.app_plan.location
  service_plan_id     = azurerm_service_plan.app_plan.id

  # public_network_access_enabled = false

  site_config {
    application_stack {
      python_version = "3.9"
    }
    # After deploying, you need to upload your code (app.py, requirements.txt)
  }
}

resource "null_resource" "deploy_app_code" {
  # Ensure the web app exists before attempting deployment
  depends_on = [azurerm_linux_web_app.webapp]

  # Triggers re-running the provisioner if the webapp ID changes (e.g., it's replaced)
  triggers = {
    webapp_id = azurerm_linux_web_app.webapp.id
    # Add a trigger based on the zip file hash if you want it to re-deploy
    # when the code changes. Requires generating the hash outside or using
    # a data source. For simplicity, we'll stick to webapp_id for now.
    # zip_hash = filebase64sha256("app_code.zip") # Assumes app_code.zip exists before plan/apply
  }

  provisioner "local-exec" {
    # Runs the Azure CLI command locally after the null_resource is created/triggered

    # Command to set the build setting (optional but good practice)
    # Note: Using 'self' is not applicable here as we are in null_resource.
    # We reference the webapp resource directly.
    command = <<EOT
      az webapp config appsettings set --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_linux_web_app.webapp.name} --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true
      echo "INFO: Pausing for 180 seconds to allow app setting to propagate..."
      sleep 180
      echo "INFO: Starting deployment of ../app_code.zip to ${azurerm_linux_web_app.webapp.name}..." 
      az webapp deploy --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_linux_web_app.webapp.name} --src-path ../app_code.zip --type zip --timeout 900
      echo "INFO: Deployment command initiated."
    EOT

    interpreter = ["bash", "-c"] # Or ["pwsh", "-Command"] on Windows

    # Optional: Define environment variables if needed by the script
    # environment = {
    #   VAR = "value"
    # }
  }
}