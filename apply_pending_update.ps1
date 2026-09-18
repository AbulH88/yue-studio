param([Parameter(Mandatory = $true)][string]$InstallRoot)

$ErrorActionPreference = 'Stop'
$updates = Join-Path $InstallRoot '.updates'
$pendingPath = Join-Path $updates 'pending-update.json'
if (-not (Test-Path -LiteralPath $pendingPath)) { exit 0 }

$pending = Get-Content -LiteralPath $pendingPath -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $pending.archive)) { Remove-Item -LiteralPath $pendingPath; exit 0 }
$stage = Join-Path $updates ("stage-" + $pending.version)
Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -LiteralPath $pending.archive -DestinationPath $stage -Force
$candidate = if (Test-Path -LiteralPath (Join-Path $stage 'yue_studio\app.py')) { $stage } else { Get-ChildItem -LiteralPath $stage -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'yue_studio\app.py') } | Select-Object -First 1 -ExpandProperty FullName }
if (-not $candidate) { throw 'The downloaded update does not contain YuE Studio.' }

$preserve = @('.git', '.updates', 'models', 'projects', 'exports', 'yue_studio\studio.config.json')
Get-ChildItem -LiteralPath $candidate -Force | Where-Object { $preserve -notcontains $_.Name } | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $InstallRoot -Recurse -Force
}
Set-Content -LiteralPath (Join-Path $updates 'installed-version.txt') -Value $pending.version
Remove-Item -LiteralPath $pendingPath -Force
Remove-Item -LiteralPath $stage -Recurse -Force
