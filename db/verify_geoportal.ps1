<# Verifica sin modificar geoportal_db. La contraseña no se muestra ni se guarda. #>
[CmdletBinding()]
param(
    [string] $PostgresBin = 'C:\Program Files\PostgreSQL\17\bin',
    [string] $HostName = '127.0.0.1',
    [int] $Port = 5432,
    [string] $AppUser = 'geoportal_app'
)

$ErrorActionPreference = 'Stop'
$Psql = Join-Path $PostgresBin 'psql.exe'
if (-not (Test-Path -LiteralPath $Psql)) { throw "No se encontró psql.exe en $PostgresBin" }
$secure = Read-Host 'Contraseña de geoportal_app' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    & $Psql -X -v ON_ERROR_STOP=1 -w -h $HostName -p $Port -U $AppUser -d geoportal_db -c "SELECT current_database(), PostGIS_Full_Version(); SELECT count(*) AS catalog_assets FROM geoportal.raster_assets;"
    if ($LASTEXITCODE -ne 0) { throw "psql terminó con código $LASTEXITCODE." }
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
