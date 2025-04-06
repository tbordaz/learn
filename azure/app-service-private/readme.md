# Azure Private Endpoint Demo Flow

## Phase 1: Initial Setup with Public Access

1. Deploy the base infrastructure using Terraform:
```bash
cd demo-app-service
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

2. Deploy the application code:
```bash
# Get the resource group and web app name from terraform output
resource_group_name=$(terraform output -raw resource_group_name)
web_app_name=$(terraform output -raw web_app_hostname)

# Deploy the app code
cd ../app_code
zip -r ../app_code.zip .
cd ..
az webapp deploy --resource-group $resource_group_name --name $web_app_name --src-path app_code.zip
```

3. Test public access:
- Open browser and navigate to `https://<web_app_name>.azurewebsites.net`
- You should see a welcome message with your client IP address
- Click the link to `/getmyip` to see the app service's outbound IP

## Phase 2: Add Private Endpoint and Restrict Public Access

1. Create Private Endpoint:
```bash
# Get the web app resource ID
webapp_id=$(az webapp show --resource-group $resource_group_name --name $web_app_name --query id -o tsv)

# Create private DNS zone if it doesn't exist
az network private-dns zone create \
    --resource-group $resource_group_name \
    --name privatelink.azurewebsites.net

# Create DNS zone link
az network private-dns link vnet create \
    --resource-group $resource_group_name \
    --zone-name privatelink.azurewebsites.net \
    --name my-vnet-link \
    --virtual-network $(terraform output -raw vnet_name) \
    --registration-enabled false

# Create private endpoint
az network private-endpoint create \
    --name "${web_app_name}-pe" \
    --resource-group $resource_group_name \
    --vnet-name $(terraform output -raw vnet_name) \
    --subnet snet-vm \
    --private-connection-resource-id $webapp_id \
    --group-id sites \
    --connection-name "${web_app_name}-psc"
```

2. Restrict public access:
```bash
az webapp update \
    --resource-group $resource_group_name \
    --name $web_app_name \
    --set siteConfig.publicNetworkAccess=Disabled
```

3. Test access:
- Browser access should now fail
- SSH into the demo VM:
```bash
$(terraform output -raw vm_ssh_command)
```
- From VM, curl the app service:
```bash
curl https://$(terraform output -raw web_app_hostname)
curl https://$(terraform output -raw web_app_hostname)/getmyip
```
- The `/getmyip` endpoint will show the app service's outbound IP is still public
- Discuss how private endpoint is ingress-only and outbound traffic still goes through public internet

## Phase 3: VNet Integration and NAT Gateway

1. Enable VNet Integration:
```bash
web_app_name=$(terraform output -raw web_app_name)
resource_group_name=$(terraform output -raw resource_group_name)

az webapp vnet-integration add \
    --resource-group $resource_group_name \
    --name $web_app_name \
    --vnet $(terraform output -raw vnet_name) \
    --subnet snet-appintegration
```

2. Test outbound access:
- SSH into VM and curl the `/getmyip` endpoint
- Show that outbound IP is still public
- Discuss that VNet integration alone doesn't force outbound through VNet

```bash
$(terraform output -raw vm_ssh_command)
```
- From VM, curl the app service:
```bash
web_app_hostname="pedemo-pcl20250330-webapp-dbhiie.azurewebsites.net"
curl https://$web_app_hostname
curl https://$web_app_hostname/getmyip

3. Associate NAT Gateway for outbound access:


4. manually associate UDR to app submet to demonstrate enterprise environment.  
Show fake IP for default route

5. Enable VNet route all:
```bash
az webapp update \
    --resource-group $resource_group_name \
    --name $web_app_name \
    --set siteConfig.vnetRouteAllEnabled=true
```

6. Test and demonstrate:
- SSH into VM and curl the `/getmyip` endpoint
- Show that access fails due to UDR blocking internet access
- Discuss how this simulates enterprise environment with restricted internet access

7. Remove UDR default route to allow NAT Gateway to work:


# Test again
curl https://<web_app_name>.azurewebsites.net/getmyip
```
- Show that outbound IP now matches NAT Gateway's public IP
- Discuss how this proves private outbound through NAT Gateway

## Cleanup

When done with the demo:
```bash
# Delete all resources
cd demo-app-service
terraform destroy
``` 