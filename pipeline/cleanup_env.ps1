Param(
  [switch]$Force
)

Write-Host "=== Pipeline Environment Cleanup ===" -ForegroundColor Cyan
$paths = @(
  '.venv',
  'work',
  'models',
  'tools_cache/rhubarb*.zip'
)

Get-ChildItem -Path . -Filter *.lipsync.json | ForEach-Object { $paths += $_.FullName }
Get-ChildItem -Path . -Filter *.wav | ForEach-Object { $paths += $_.FullName }
Get-ChildItem -Path . -Filter *.m4a | ForEach-Object { $paths += $_.FullName }

foreach ($p in $paths | Sort-Object -Unique) {
  if (Test-Path $p) {
    if (-not $Force) {
      $ans = Read-Host "Delete $p ? (y/N)"
      if ($ans -notin @('y','Y')) { continue }
    }
    Write-Host "Removing $p" -ForegroundColor Yellow
    Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue
  }
}
Write-Host "Cleanup complete." -ForegroundColor Green
