<#
.SYNOPSIS
    Maps Entra ID (Azure AD) groups to Nexus IQ roles using the Nexus IQ API.

.DESCRIPTION
    This script automates the process of assigning Entra ID groups to specific roles
    within Nexus IQ. It retrieves role IDs, assigns a designated group to those roles,
    and verifies the assignments. It uses the Nexus IQ REST API for these operations.
    https://support.sonatype.com/hc/en-us/articles/4402929272851-Entra-ID-FKA-Azure-AD-SAML-Integration-with-Sonatype-Platform

.PARAMETER NexusIQBaseUrl
    The base URL of your Nexus IQ server (e.g., "http://nexusiq.example.com").

.PARAMETER AdminGroupId
    The Entra ID Object ID of the group that should be assigned to the roles.

.PARAMETER NexusIQAdminUsername
    The username of a Nexus IQ built-in administrator account.

.EXAMPLE
    .\Map-SAMLGroupsToNexusRoles.ps1 -NexusIQBaseUrl "http://nexusiq.example.com" -AdminGroupId "a1b2c3d4-e5f6-7890-1234-567890abcdef" -NexusIQAdminUsername "admin" 

.NOTES
    Author: Peter Chua-Lao
    Date: 11/02/2025
#>

param (
    [Parameter(Mandatory = $true, HelpMessage = "The base URL of your Nexus IQ server (e.g., 'http://nexusiq.example.com')")]
    [string]$NexusIQBaseUrl,

    [Parameter(Mandatory = $true, HelpMessage = "The Entra ID Object ID of the group to assign to roles")]
    [string]$AdminGroupId,

    [Parameter(HelpMessage = "Nexus IQ built-in admin username")]
    [string]$NexusIQAdminUsername = "admin"
)

# Prompt for admin credentials
$NexusIQAdminPassword = Read-Host -Prompt "Enter Nexus IQ built-in admin password" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($NexusIQAdminPassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
$pair = "${NexusIQAdminUsername}:${plainPassword}"
$encodedCreds = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes($pair))

# Create default header with authorization
$headers = @{
    Authorization = "Basic $encodedCreds"
    "Content-Type" = "application/json"
}

# Helper function for API calls that handles error reporting
function Invoke-NexusAPI {
    param (
        [Parameter(Mandatory = $true)][string]$Endpoint,
        [Parameter(Mandatory = $false)][string]$Method = "Get",
        [Parameter(Mandatory = $false)]$Body = $null
    )

    $uri = "$NexusIQBaseUrl$Endpoint"
    try {
        Write-Verbose "Invoking API: Method=$Method, URI=$uri"
        if ($Body) {
            return Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -Body $Body
        } else {
            return Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers
        }
    }
    catch {
        Write-Error "Error calling $uri" 
        Write-Error "Status Code:" $($_.Exception.Response.StatusCode.value__)
        Write-Error "Status Description:" $($_.Exception.Response.StatusDescription)
        throw
    }
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

# Main script logic
try {
    # 1. Retrieve roles and extract necessary role IDs
    $rolesResponse = Invoke-NexusAPI -Endpoint "/api/v2/roles"
    Write-Host "Roles retrieved:" ( $rolesResponse | ConvertTo-Json -Depth 5 )

    # 2. Extract role IDs for System Administrator and Policy Administrator
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

    # 3. Assign group to roles
    Assign-GroupToRole -RoleId $sysadminRoleId -GroupId $adminGroupID
    Assign-GroupToRole -RoleId $policyAdminRoleId -GroupId $adminGroupID

    # 4. Confirm the group assignments via status query
    Write-Host "Verifying role memberships..."
    $statusResponse = Invoke-NexusAPI -Endpoint "/api/v2/roleMemberships/global"
    Write-Host "Current role memberships:" ( $statusResponse | ConvertTo-Json -Depth 5 )
}
catch {
    Write-Error "An error occurred while mapping groups to roles."
    Write-Error $_.Exception.Message
}


# get all applications - https://help.sonatype.com/en/application-rest-api.html
# $endpoint = "/api/v2/applications"
# $response = Invoke-NexusAPI -Endpoint $endpoint -Method "GET"
# $response | ConvertTo-Json -Depth 5 
