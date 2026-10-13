# Windows PowerShell: .\run.ps1 (Git and Python environment managed by uv).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
uv sync --locked --python 3.12
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --no-sync python -m seo_optimizer.local @args
exit $LASTEXITCODE
