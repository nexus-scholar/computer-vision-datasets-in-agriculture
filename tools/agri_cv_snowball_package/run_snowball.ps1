param(
  [string]$Out = "outputs/snowball_manual_$(Get-Date -Format 'yyyy-MM-dd_HHmm')",
  [string]$SeedIds = ""
)
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
Push-Location $RepoRoot
try {
  $argsList = @(
    "tools/agri_cv_snowball_package/scripts/collect_openalex_semantic_scholar_snowball.py",
    "--input", "tools/agri_cv_snowball_package/input/seed_papers_manifest.csv",
    "--out", $Out,
    "--providers", "both"
  )
  if ($SeedIds) { $argsList += @("--seed-ids", $SeedIds) }
  uv run python @argsList
}
finally { Pop-Location }
