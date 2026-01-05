<#!
Helper to launch AzureHound via Docker without persisting credentials.
- Prompts for tenant, auth method, and output folder.
- Does NOT store secrets; operators provide them at runtime.
- Produces BloodHound-compatible JSON files under the chosen output directory.
#>

param(
    [string]$AzureHoundImage = "ghcr.io/specterops/azurehound:2.2.0",
    [string]$Tenant,
    [ValidateSet("devicecode","client-secret")]
    [string]$AuthType = "devicecode",
    [string]$ClientId,
    [string]$ClientSecret,
    [string]$Output = "$PWD/azurehound-output"
)

if (-not $Tenant) {
    $Tenant = Read-Host "Enter tenant ID or verified domain"
}

if (-not (Test-Path $Output)) {
    New-Item -ItemType Directory -Path $Output | Out-Null
}

Write-Host "Pulling AzureHound image $AzureHoundImage ..."
docker pull $AzureHoundImage | Out-Null

$baseCmd = @(
    "docker run --rm -it",
    "-v `"$Output:/data`"",
    $AzureHoundImage,
    "collect",
    "--tenant $Tenant",
    "--output /data"
)

if ($AuthType -eq "client-secret") {
    if (-not $ClientId) { $ClientId = Read-Host "Enter client ID" }
    if (-not $ClientSecret) { $ClientSecret = Read-Host "Enter client secret" }
    $baseCmd += @("--client-id $ClientId", "--client-secret $ClientSecret")
} else {
    $baseCmd += "--auth-type devicecode"
}

Write-Host "Launching AzureHound..."
$cmd = $baseCmd -join ' '
Write-Host $cmd
Invoke-Expression $cmd

Write-Host "Collection complete. JSON files are in $Output" -ForegroundColor Green
