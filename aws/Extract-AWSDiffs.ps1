<#
.SYNOPSIS
AWS Accelerator Diff Extractor and Viewer

.DESCRIPTION
This script downloads, extracts, and displays AWS Accelerator diff files.
It handles AWS SSO login, downloads diff files from S3, extracts them to a local directory, and displays the content in an Out-GridView.
Starting with LZA v1.11.0, the diff files are generated during the upgrade process and stored in an S3 bucket.

.PARAMETER s3Path
The S3 path where the diff files are located.

.PARAMETER localPath
The local path where the diff files will be downloaded and extracted.

.EXAMPLE
.\Extract-AWSDiffs.ps1 -s3Path "s3://your-bucket/your-path" -localPath "diffs"

.NOTES
File Name      : Extract-AWSDiffs.ps1
Author         : Peter Chua-Lao (Updated)
Prerequisite   : PowerShell 5.1 or later, AWS CLI, AWS SSO access
#>

# Parameters
param(
    [string]$s3Path = "s3://aws-accelerator-pipeline-xxx",
    [string]$localPath = "diffs-$(Get-Date -Format 'yyyyMMdd')"
)

# Function to ensure 7Zip4PowerShell module is installed
function Ensure-7ZipModule {
    if (-not (Get-Module -ListAvailable -Name 7Zip4PowerShell)) {
        Write-Host "Installing 7Zip4PowerShell module..."
        Install-Module -Name 7Zip4PowerShell -Scope CurrentUser -Force
    }
    Import-Module 7Zip4PowerShell
}

# Function to handle AWS SSO login
function Invoke-AWSSSOLogin {
    $profiles = @("master-admin", "master-dev")
    $selectedProfile = $profiles | Out-GridView -Title "Select AWS SSO Profile" -OutputMode Single

    if ($selectedProfile) {
        $env:AWS_PROFILE = $selectedProfile
        Write-Host "Logging in with profile: $selectedProfile"
        aws sso login
        if ($LASTEXITCODE -ne 0) {
            throw "AWS SSO login failed. Please check your credentials and try again."
        }
    } else {
        throw "No profile selected. Exiting script."
    }
}

# Main execution
try {
    # Perform AWS SSO login
    Invoke-AWSSSOLogin

    # Download the diff files from S3
    Write-Host "Downloading diff files from S3..."
    aws s3 sync $s3Path $localPath

    # Ensure 7Zip module is installed
    Ensure-7ZipModule

    # Store the original location
    $currentLocation = Get-Location
    # Set the working directory
    $workingDirectory = Join-Path (Get-Location) $localPath
    Set-Location $workingDirectory

    # Extract .tgz files
    Write-Host "Extracting .tgz files..."
    Get-ChildItem -Filter *.tgz | ForEach-Object {
        Expand-7Zip -ArchiveFileName $_.FullName -TargetPath $PWD.Path
    }

    # Extract .tar files
    Write-Host "Extracting .tar files to $workingDirectory..."
    Get-ChildItem -Filter *.tar | ForEach-Object {
        Expand-7Zip -ArchiveFileName $_.FullName -TargetPath $PWD.Path
    }

    # Clean up temporary files
    Write-Host "Cleaning up temporary files..."
    Remove-Item *.tar
    Remove-Item *.tgz

    # View .diff files directly in Out-GridView
    Write-Host "Viewing .diff files..."
    Get-Content -Path "$workingDirectory\*.diff" | Out-GridView -Title "AWS Accelerator Diff Files"

    Write-Host "Extraction and viewing complete. Diff files are available in the '$workingDirectory' directory."

} catch {
    Write-Error "An error occurred: $_"
} finally {
    # Return to the original directory
    Set-Location $currentLocation
}
