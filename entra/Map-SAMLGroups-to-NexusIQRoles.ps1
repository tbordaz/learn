# script to map SAML groups to Nexus IQ roles
# Author: Peter Chua-Lao
# date: 10/02/2025
# https://support.sonatype.com/hc/en-us/articles/4402929272851-Entra-ID-FKA-Azure-AD-SAML-Integration-with-Sonatype-Platform

# Define base URL and admin group ID
$baseUrl = "<http://nexusiq.server">
$adminGroupID = "<Entra Object ID>"  # nexus-admins group

# Prompt for admin credentials
$username = "admin"
$password = Read-Host -Prompt "Enter Nexus IQ built-in admin password: " -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
$pair = "$username:$password"
$encodedCreds = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes($pair))

# Create default header with authorization
$headers = @{
    Authorization = "Basic $encodedCreds"
}

# Helper function for API calls that handles error reporting
function Invoke-NexusAPI {
    param (
        [Parameter(Mandatory = $true)][string]$Endpoint,
        [Parameter(Mandatory = $false)][string]$Method = "Get",
        [Parameter(Mandatory = $false)]$Body = $null
    )

    $uri = "$baseUrl$Endpoint"
    try {
        if ($Body) {
            return Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -Body $Body
        } else {
            return Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers
        }
    }
    catch {
        Write-Host "Error calling $uri" -ForegroundColor Red
        Write-Host "Status Code:" $($_.Exception.Response.StatusCode.value__)
        Write-Host "Status Description:" $($_.Exception.Response.StatusDescription)
        throw
    }
}

# Retrieve roles and extract necessary role IDs
$rolesResponse = Invoke-NexusAPI -Endpoint "/api/v2/roles"
Write-Host "Roles retrieved:" ( $rolesResponse | ConvertTo-Json -Depth 5 )

$sysadminRoleId   = ($rolesResponse.roles | Where-Object { $_.name -eq "System Administrator" }).id
$policyAdminRoleId = ($rolesResponse.roles | Where-Object { $_.name -eq "Policy Administrator" }).id

# Logging discovered Role IDs for clarity
if ($sysadminRoleId) {
    Write-Host "Found System Administrator Role ID:" $sysadminRoleId
} else {
    Write-Host "System Administrator Role not found" -ForegroundColor Red
}

if ($policyAdminRoleId) {
    Write-Host "Found Policy Administrator Role ID:" $policyAdminRoleId
} else {
    Write-Host "Policy Administrator Role not found" -ForegroundColor Red
}

# Check if both role IDs were found
if (-not $sysadminRoleId -or -not $policyAdminRoleId) {
    Write-Error "Could not locate one or more required role IDs. Exiting..."
    return
}

# Function to assign a group to a role
function Assign-GroupToRole {
    param (
        [string]$RoleId,
        [string]$GroupId
    )
    $endpoint = "/api/v2/roleMemberships/global/role/$RoleId/group/$GroupId"
    $response = Invoke-NexusAPI -Endpoint $endpoint -Method "PUT"
    Write-Host "Assigned group $GroupId to role $RoleId:" ( $response | ConvertTo-Json -Depth 5 )
}

# Assign the Nexus-admin group to the required roles
Assign-GroupToRole -RoleId $sysadminRoleId -GroupId $adminGroupID
Assign-GroupToRole -RoleId $policyAdminRoleId -GroupId $adminGroupID

# Confirm the group assignments via status query
$statusResponse = Invoke-NexusAPI -Endpoint "/api/v2/roleMemberships/global"
Write-Host "Current role memberships:" ( $statusResponse | ConvertTo-Json -Depth 5 )


# get all applications - https://help.sonatype.com/en/application-rest-api.html
$endpoint = "/api/v2/applications"
$response = Invoke-NexusAPI -Endpoint $endpoint -Method "GET"
$response | ConvertTo-Json -Depth 5 
