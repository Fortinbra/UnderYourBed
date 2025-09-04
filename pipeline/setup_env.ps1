Param(
  [string]$Python = "",
  [string]$RhubarbUrl = "",           # Optional explicit URL override
  [string]$RhubarbVersion = "1.14.0",  # Version to attempt if URL not supplied (supports 1.14/1.14.0 patterns)
  [string]$ToolsDir = "tools_cache",
  [switch]$WithVoskSmall,              # Download small Vosk English model
  [string]$VoskModelUrl = "",          # Custom Vosk model URL
  [string]$ModelsDir = "models",
  [switch]$SkipRhubarb,
  [switch]$NoActivate
)

$ErrorActionPreference = 'Stop'

Write-Host "=== Offline Pipeline Environment Setup ===" -ForegroundColor Cyan

# Resolve script directory (so script can be run from anywhere)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# If user accidentally passed '.' as first positional argument, ignore it
if ($Python -and ($Python -eq '.' -or $Python -eq './' -or $Python -eq '.\\')) { $Python = "" }

# Function to test a python candidate
function Test-PythonCandidate {
  param([string]$Cmd)
  try { & $Cmd --version *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

# If Python param supplied, validate it; if invalid, clear so auto-detect runs
if ($Python) {
  if (-not (Test-PythonCandidate $Python)) {
    Write-Host "Provided -Python '$Python' is not executable; attempting auto-detect..." -ForegroundColor Yellow
    $Python = ""
  }
}

# Auto-detect if still empty
if (-not $Python) {
  foreach ($candidate in @('python','py','python3')) {
    if (Test-PythonCandidate $candidate) { $Python = $candidate; break }
  }
}
if (-not $Python) { throw "Python not found. Install Python 3.11+ or re-run with -Python path." }

Write-Host "Using Python executable: $Python"

if (-not (Test-Path .venv)) {
  Write-Host "Creating virtual environment (.venv)..."
  & $Python -m venv .venv
} else {
  Write-Host ".venv already exists; skipping creation." -ForegroundColor Yellow
}

# Compute venv python & pip without relying on activation
$VenvPython = Join-Path $ScriptDir ".venv/ScriptS/python.exe"
if (-not (Test-Path $VenvPython)) { $VenvPython = Join-Path $ScriptDir ".venv/Scripts/python.exe" }
if (-not (Test-Path $VenvPython)) { $VenvPython = Join-Path $ScriptDir ".venv/bin/python" }
if (-not (Test-Path $VenvPython)) { throw "Could not locate venv python executable." }

Write-Host "Upgrading pip..."
& $VenvPython -m pip install --upgrade pip

Write-Host "Installing Python dependencies from requirements.txt..."
& $VenvPython -m pip install -r requirements.txt
if ($WithVoskSmall -or $VoskModelUrl) {
  Write-Host "Ensuring optional alignment dependencies (vosk, rapidfuzz)..."
  & $VenvPython -m pip install vosk rapidfuzz --upgrade
}

Write-Host "Note: Ensure ffmpeg is installed (winget install Gyan.FFmpeg or choco install ffmpeg, etc.)." -ForegroundColor Yellow

if (-not $SkipRhubarb) {
  New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null
  $RhubarbExe = Join-Path $ToolsDir "rhubarb.exe"
  if (-not (Test-Path $RhubarbExe)) {
    # Build candidate URL list if user did not supply explicit URL
    $candidateUrls = @()
    if ($RhubarbUrl) {
      $candidateUrls += $RhubarbUrl
    } else {
      # Build version tokens (e.g., 1.14.0 and 1.14) to handle differing tag naming
      $verFull = $RhubarbVersion
      $verShort = if ($RhubarbVersion -match '^([0-9]+\.[0-9]+)\.0$') { $Matches[1] } else { $RhubarbVersion }
      foreach ($ver in @($verFull, $verShort) | Select-Object -Unique) {
        $base = "https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v$ver";
        # Include historical lowercase patterns and new capitalized naming (e.g. Rhubarb-Lip-Sync-1.14.0-Windows.zip)
        $candidateUrls += @(
          "$base/Rhubarb-Lip-Sync-$ver-Windows.zip",
          "$base/rhubarb-lip-sync-$ver-win64.zip",
          "$base/rhubarb-lip-sync-$ver-win.zip",
          "$base/rhubarb-lip-sync-$ver-win32.zip"
        )
      }
    }

  # Final fallback: if rhubarb.exe exists but res still missing, try to locate any res folder within tools_cache
  $finalExe = Join-Path $ToolsDir 'rhubarb.exe'
  $expectedRes = Join-Path $ToolsDir 'res'
  if (Test-Path $finalExe -and -not (Test-Path $expectedRes)) {
    Write-Host "Attempting fallback resource discovery..." -ForegroundColor Yellow
    $dictMatch = Get-ChildItem $ToolsDir -Recurse -Filter 'cmudict-en-us.dict' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($dictMatch) {
      $candidateRes = (Split-Path (Split-Path $dictMatch.FullName -Parent) -Parent)
      # Ensure this folder actually contains sphinx subfolder
      if (Test-Path (Join-Path $candidateRes 'sphinx')) {
        Write-Host "Copying discovered resource folder from $candidateRes to $expectedRes" -ForegroundColor Cyan
        Copy-Item $candidateRes $expectedRes -Recurse -Force
      }
    }
    if (-not (Test-Path $expectedRes)) {
      Write-Host "Rhubarb resources still missing; manual copy required (place 'res' beside rhubarb.exe)." -ForegroundColor Red
    } else {
      Write-Host "Rhubarb resources repaired via fallback." -ForegroundColor Green
    }
  }

    $downloaded = $false
    $RhubarbZip = Join-Path $ToolsDir "rhubarb.zip"
    foreach ($url in $candidateUrls) {
      Write-Host "Attempting Rhubarb download: $url" -ForegroundColor Cyan
      try {
        Invoke-WebRequest -Uri $url -OutFile $RhubarbZip -UseBasicParsing -ErrorAction Stop
        $downloaded = $true
        break
      } catch {
        Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Yellow
      }
    }
    if (-not $downloaded) {
      Write-Host "Could not download Rhubarb automatically." -ForegroundColor Red
      Write-Host "Please manually download a Windows release from:" -ForegroundColor Yellow
      Write-Host "  https://github.com/DanielSWolf/rhubarb-lip-sync/releases" -ForegroundColor Yellow
      Write-Host "Place rhubarb.exe into: $ToolsDir" -ForegroundColor Yellow
    } else {
      Write-Host "Extracting Rhubarb..."
      try {
        Expand-Archive -Path $RhubarbZip -DestinationPath $ToolsDir -Force
      } catch {
        Write-Host "Extraction failed: $($_.Exception.Message)" -ForegroundColor Red
      }
      $found = Get-ChildItem $ToolsDir -Recurse -Filter rhubarb.exe | Select-Object -First 1
      if ($found) {
        Copy-Item $found.FullName $RhubarbExe -Force
        # Ensure 'res' directory (with sphinx data) is copied next to the exe so relative lookup works
        $parentDir = Split-Path $found.FullName -Parent
        $srcRes = Join-Path $parentDir 'res'
        $destRes = Join-Path $ToolsDir 'res'
        if (Test-Path $srcRes -and -not (Test-Path $destRes)) {
          Write-Host "Copying Rhubarb resource folder..."
          Copy-Item $srcRes $destRes -Recurse -Force
        }
      }
      if (Test-Path $RhubarbZip) { Remove-Item $RhubarbZip -Force }
    }
  } else {
    Write-Host "Rhubarb already present at $RhubarbExe"
    # If exe exists but res folder missing, prompt user
    $destRes = Join-Path $ToolsDir 'res'
    if (-not (Test-Path $destRes)) {
      Write-Host "Rhubarb resources folder missing (expected $destRes). Attempting automatic re-download to restore resources..." -ForegroundColor Yellow
      # Build candidate URLs again and attempt download solely for resources
      $candidateUrls = @()
      if ($RhubarbUrl) {
        $candidateUrls += $RhubarbUrl
      } else {
        $verFull = $RhubarbVersion
        $verShort = if ($RhubarbVersion -match '^([0-9]+\.[0-9]+)\.0$') { $Matches[1] } else { $RhubarbVersion }
        foreach ($ver in @($verFull, $verShort) | Select-Object -Unique) {
          $base = "https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v$ver";
          $candidateUrls += @(
            "$base/Rhubarb-Lip-Sync-$ver-Windows.zip",
            "$base/rhubarb-lip-sync-$ver-win64.zip",
            "$base/rhubarb-lip-sync-$ver-win.zip",
            "$base/rhubarb-lip-sync-$ver-win32.zip"
          )
        }
      }
      $downloaded = $false
      $RhubarbZip = Join-Path $ToolsDir "rhubarb_redownload.zip"
      foreach ($url in $candidateUrls) {
        Write-Host "Attempting resource re-download: $url" -ForegroundColor Cyan
        try {
          Invoke-WebRequest -Uri $url -OutFile $RhubarbZip -UseBasicParsing -ErrorAction Stop
          $downloaded = $true
          break
        } catch {
          Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
      }
      if ($downloaded) {
        try {
          Expand-Archive -Path $RhubarbZip -DestinationPath $ToolsDir -Force
          $foundRes = Get-ChildItem $ToolsDir -Recurse -Filter cmudict-en-us.dict | Select-Object -First 1
          if ($foundRes) {
            $parentRes = Split-Path (Split-Path $foundRes.FullName -Parent) -Parent
            if (Test-Path (Join-Path $parentRes 'res')) {
              $srcRes = Join-Path $parentRes 'res'
              if (-not (Test-Path $destRes)) {
                Write-Host "Copying restored resource folder..."
                Copy-Item $srcRes $destRes -Recurse -Force
              }
            }
          }
        } catch {
          Write-Host "Resource extraction failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        if (Test-Path $RhubarbZip) { Remove-Item $RhubarbZip -Force }
      } else {
        Write-Host "Automatic re-download failed. Please manually copy 'res' next to rhubarb.exe." -ForegroundColor Red
      }
      if (-not (Test-Path $destRes)) {
        Write-Host "Resources still missing. Manual fix required." -ForegroundColor Red
      } else {
        Write-Host "Rhubarb resources restored." -ForegroundColor Green
      }
    }
  }
} else {
  Write-Host "Skipping Rhubarb download (per --SkipRhubarb)." -ForegroundColor Yellow
}

if (-not $NoActivate) {
  Write-Host "Activating virtual environment..."
  $activate = if ($IsWindows) { ".venv/Scripts/Activate.ps1" } else { ".venv/bin/activate" }
  if (Test-Path $activate) {
    if ($IsWindows) { . $activate } else { Write-Host "Run: source $activate" -ForegroundColor Yellow }
  } else {
    Write-Host "Activation script not found; continuing without activation." -ForegroundColor Yellow
  }
} else {
  Write-Host "Skipping activation (per --NoActivate)."
}

Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Example (within venv): $VenvPython generate_lipsync.py --audio sample.wav --rhubarb tools_cache/rhubarb.exe --out out.json"
Write-Host "If rhubarb.exe missing, download manually and re-run any generation command." -ForegroundColor Yellow
Write-Host "If activation failed due to policy, run: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned" -ForegroundColor Yellow

if ($WithVoskSmall -or $VoskModelUrl) {
  $mdlBase = Join-Path $ScriptDir $ModelsDir
  New-Item -ItemType Directory -Force -Path $mdlBase | Out-Null
  $voskUrl = if ($VoskModelUrl) { $VoskModelUrl } else { 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip' }
  $zipPath = Join-Path $mdlBase 'vosk_model.zip'
  Write-Host "Downloading Vosk model: $voskUrl" -ForegroundColor Cyan
  try {
    Invoke-WebRequest -Uri $voskUrl -OutFile $zipPath -UseBasicParsing -ErrorAction Stop
    Write-Host "Extracting Vosk model..." -ForegroundColor Cyan
    Expand-Archive -Path $zipPath -DestinationPath $mdlBase -Force
    Remove-Item $zipPath -Force
    Write-Host "Vosk model ready under $mdlBase" -ForegroundColor Green
  } catch {
    Write-Host "Vosk model download failed: $($_.Exception.Message)" -ForegroundColor Red
  }
}
