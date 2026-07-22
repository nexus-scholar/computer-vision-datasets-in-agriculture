param(
    [Parameter(Mandatory=$false)]
    [string]$Repo = ".",
    [switch]$Force,
    [switch]$ApplyPatches
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Installer = Join-Path $PackageRoot "install.py"

$argsList = @($Installer, "--repo", $Repo)
if ($Force) { $argsList += "--force" }
python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$patches = @(
    (Join-Path $PackageRoot "patches/0001-fix-inventory-output-path.patch"),
    (Join-Path $PackageRoot "patches/0002-harden-snowball-collector.patch")
)

foreach ($patch in $patches) {
    git -C $Repo apply --check $patch
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Patch check failed: $patch"
        exit $LASTEXITCODE
    }
}

if ($ApplyPatches) {
    foreach ($patch in $patches) {
        git -C $Repo apply $patch
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    Write-Host "Overlay installed and both source patches applied."
} else {
    Write-Host "Overlay installed. Both source patches pass git apply --check."
    Write-Host "Re-run with -ApplyPatches after reviewing the patches."
}
