<#
Provisiona exclusivamente geoportal_db y geoportal_app en PostgreSQL local.
No enumera, modifica ni elimina las bases existentes. Las dos contraseñas se
piden mediante Read-Host -AsSecureString, se usan solo en memoria para psql y
no se imprimen ni se agregan al historial.
#>
[CmdletBinding()]
param(
    [string] $PostgresBin = 'C:\Program Files\PostgreSQL\17\bin',
    [string] $HostName = '127.0.0.1',
    [int] $Port = 5432,
    [string] $AdminUser = 'postgres'
)

$ErrorActionPreference = 'Stop'
$DatabaseName = 'geoportal_db'
$AppUser = 'geoportal_app'
$Psql = Join-Path $PostgresBin 'psql.exe'
$Migration = Join-Path $PSScriptRoot '001_geoportal_catalog.sql'

if (-not (Test-Path -LiteralPath $Psql)) { throw "No se encontró psql.exe en $PostgresBin" }
if (-not (Test-Path -LiteralPath $Migration)) { throw 'No se encontró la migración del catálogo.' }
if ($DatabaseName -notmatch '^[a-z][a-z0-9_]*$' -or $AppUser -notmatch '^[a-z][a-z0-9_]*$') {
    throw 'Los identificadores internos no son seguros.'
}

function Convert-SecureText([securestring] $SecureValue) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

function Invoke-Psql([string] $Database, [string] $User, [string] $Password, [string[]] $Arguments) {
    $env:PGPASSWORD = $Password
    try {
        & $Psql -X -v ON_ERROR_STOP=1 -w -h $HostName -p $Port -U $User -d $Database @Arguments
        if ($LASTEXITCODE -ne 0) { throw "psql terminó con código $LASTEXITCODE." }
    }
    finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
}

function Invoke-PsqlInput([string] $Database, [string] $User, [string] $Password, [string] $Sql) {
    # La contraseña del rol de aplicación viaja por stdin a psql, nunca como
    # argumento de proceso ni salida de consola.
    $env:PGPASSWORD = $Password
    try {
        $Sql | & $Psql -X -v ON_ERROR_STOP=1 -w -h $HostName -p $Port -U $User -d $Database
        if ($LASTEXITCODE -ne 0) { throw "psql terminó con código $LASTEXITCODE." }
    }
    finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
}

$AdminPassword = Convert-SecureText (Read-Host 'Contraseña del administrador PostgreSQL' -AsSecureString)
$AppPassword = Convert-SecureText (Read-Host 'Nueva contraseña para geoportal_app' -AsSecureString)
if ([string]::IsNullOrWhiteSpace($AdminPassword) -or [string]::IsNullOrWhiteSpace($AppPassword)) {
    throw 'Las contraseñas no pueden quedar vacías.'
}

try {
    $dbExists = Invoke-Psql 'postgres' $AdminUser $AdminPassword @('-Atc', "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName';")
    $roleExists = Invoke-Psql 'postgres' $AdminUser $AdminPassword @('-Atc', "SELECT 1 FROM pg_roles WHERE rolname = '$AppUser';")
    if (($dbExists -join '').Trim() -eq '1') { throw "$DatabaseName ya existe; el script no lo modifica." }
    if (($roleExists -join '').Trim() -eq '1') { throw "$AppUser ya existe; el script no altera roles existentes." }

    $escapedPassword = $AppPassword.Replace("'", "''")
    Invoke-PsqlInput 'postgres' $AdminUser $AdminPassword "CREATE ROLE $AppUser LOGIN PASSWORD '$escapedPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;"
    Invoke-Psql 'postgres' $AdminUser $AdminPassword @('-c', "CREATE DATABASE $DatabaseName WITH OWNER $AppUser TEMPLATE template0 ENCODING 'UTF8';")
    Invoke-Psql $DatabaseName $AdminUser $AdminPassword @('-c', 'CREATE EXTENSION postgis;')
    Invoke-Psql $DatabaseName $AppUser $AppPassword @('-f', $Migration)
    Write-Output 'geoportal_db quedó creada con PostGIS y su catálogo. Ninguna otra base fue modificada.'
    Write-Output 'Configura GEOPORTAL_DATABASE_URL y un directorio privado antes de iniciar la API.'
}
finally {
    $AdminPassword = $null
    $AppPassword = $null
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
