param(
  [string]$ProjectRef = "hvrbhfeprzjuqcyzcuba",
  [string]$DatabaseUser = "postgres"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$migrationPath = Join-Path $repoRoot "supabase\migrations\202608220002_gpu_fan_metrics.sql"

if (-not (Test-Path -LiteralPath $migrationPath)) {
  throw "Migration file was not found: $migrationPath"
}

$psql = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psql) {
  throw "psql was not found. Install PostgreSQL command-line tools first."
}

$password = Read-Host "Enter the Supabase database password" -AsSecureString
$plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
)

try {
  $env:PGPASSWORD = $plainPassword
  & $psql.Source `
    --host "db.$ProjectRef.supabase.co" `
    --port 5432 `
    --username $DatabaseUser `
    --dbname postgres `
    --file $migrationPath
} finally {
  Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}
