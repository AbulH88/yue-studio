param(
  [string]$InstallRoot = "$env:LOCALAPPDATA\YuE Studio"
)

$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$excluded = @('.git', '.updates', '__pycache__', 'studio.config.json', 'projects', 'exports', 'models')
$captionRevision = '732354f20c9dd5fa1c037d0e301e8bf837c1cf8e'
$captionModels = @(
  @{ Name = 'acestep-captioner-Q4_K_M.gguf'; Sha256 = '1c6fb97c2599dc259af70bbfc89a65da24360ba55d7b982366ca32f7e2ae8786'; Size = '4.68 GB' },
  @{ Name = 'acestep-captioner-mmproj-Q8_0.gguf'; Sha256 = '77f15ee6e123a85deb2e853ef08d791613e2350c3cd24e033e99e6bad027a8b8'; Size = '1.55 GB' }
)

function Test-VerifiedFile {
  param([string]$Path, [string]$Sha256)
  return (Test-Path -LiteralPath $Path) -and ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower() -eq $Sha256)
}

function Install-CaptionerModel {
  param([hashtable]$Model, [string]$DestinationRoot)
  $destination = Join-Path $DestinationRoot $Model.Name
  if (Test-VerifiedFile -Path $destination -Sha256 $Model.Sha256) {
    Write-Host "  Verified already: $($Model.Name)"
    return
  }
  if (Test-Path -LiteralPath $destination) {
    Write-Host "  Removing an incomplete or invalid copy of $($Model.Name)."
    Remove-Item -LiteralPath $destination -Force
  }
  $url = "https://huggingface.co/dernet/acestep-captioner-GGUF/resolve/$captionRevision/$($Model.Name)?download=true"
  Write-Host "  Downloading $($Model.Name) ($($Model.Size))..."
  & curl.exe --fail --location --retry 3 --retry-delay 2 --output $destination $url
  if ($LASTEXITCODE -ne 0) { throw "Download failed for $($Model.Name)." }
  if (-not (Test-VerifiedFile -Path $destination -Sha256 $Model.Sha256)) {
    Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
    throw "Security check failed for $($Model.Name). The invalid download was removed."
  }
  Write-Host "  Verified: $($Model.Name)"
}

Write-Host ''
Write-Host 'Step 1 of 4: Copying YuE Studio...'
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
Get-ChildItem -LiteralPath $source -Force | Where-Object { $excluded -notcontains $_.Name } | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $InstallRoot -Recurse -Force
}

Write-Host 'Step 2 of 4: Installing the local ACE-Step captioner models...'
$captionRoot = Join-Path $InstallRoot 'models\captioner'
New-Item -ItemType Directory -Path $captionRoot -Force | Out-Null
foreach ($model in $captionModels) { Install-CaptionerModel -Model $model -DestinationRoot $captionRoot }

Write-Host 'Step 3 of 4: Installing the local ACE-Step captioner engine...'
$engineInstaller = Join-Path $InstallRoot 'install_captioner_engine.ps1'
$engineRoot = Join-Path $captionRoot 'engine'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $engineInstaller -EngineRoot $engineRoot
if ($LASTEXITCODE -ne 0) { throw 'ACE-Step captioner engine installation failed.' }
if (-not (Test-Path -LiteralPath (Join-Path $engineRoot 'llama-server.exe'))) {
  throw 'ACE-Step captioner engine verification failed: llama-server.exe is missing.'
}

$launcher = Join-Path $InstallRoot 'Launch YuE Studio.cmd'

Write-Host 'Step 4 of 4: Opening YuE Studio...'
Start-Process -FilePath $launcher -WorkingDirectory $InstallRoot
Write-Host 'YuE Studio was installed or updated and is opening now.'
Write-Host 'The ACE-Step captioner is ready for local audio captioning.'
Write-Host "Installed location: $InstallRoot"
