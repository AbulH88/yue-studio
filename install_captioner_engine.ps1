param(
  [Parameter(Mandatory = $true)][string]$EngineRoot
)

$ErrorActionPreference = 'Stop'
$stockTag = 'b10796'
$stockBase = "https://github.com/ggml-org/llama.cpp/releases/download/$stockTag"
$stock = @(
  @{ Name = 'llama-b10796-bin-win-cuda-13.3-x64.zip'; Sha256 = '433b6d15595e1bad8bba550461f9765e8bb1c33d2d53977dd0e33a29138c1dbf' },
  @{ Name = 'cudart-llama-bin-win-cuda-13.3-x64.zip'; Sha256 = '1462a050eb4c684921ba51dcc4cc488a036674c3e73e9945ee705b854808d03e' }
)

New-Item -ItemType Directory -Force -Path $EngineRoot | Out-Null
$cache = Join-Path $EngineRoot '.downloads'
New-Item -ItemType Directory -Force -Path $cache | Out-Null
foreach ($item in $stock) {
  $archive = Join-Path $cache $item.Name
  if (-not (Test-Path $archive) -or (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower() -ne $item.Sha256) {
    Invoke-WebRequest -Uri "$stockBase/$($item.Name)" -OutFile $archive
  }
  if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLower() -ne $item.Sha256) { throw "Security check failed for $($item.Name)." }
  Expand-Archive -LiteralPath $archive -DestinationPath $EngineRoot -Force
}

$release = Invoke-RestMethod 'https://api.github.com/repos/koda-dernet/acestep-captioner/releases/latest'
$overlay = $release.assets | Where-Object { $_.name -match 'mtmd\.dll$' } | Select-Object -First 1
if (-not $overlay) { throw 'The compatible ACE-Step audio overlay was not found in its published release.' }
$overlayPath = Join-Path $cache 'mtmd.dll'
Invoke-WebRequest -Uri $overlay.browser_download_url -OutFile $overlayPath
Copy-Item -LiteralPath $overlayPath -Destination (Join-Path $EngineRoot 'mtmd.dll') -Force
if (-not (Test-Path (Join-Path $EngineRoot 'llama-server.exe'))) { throw 'llama-server.exe was not installed correctly.' }
