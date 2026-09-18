param(
  [string]$InstallRoot = "$env:LOCALAPPDATA\YuE Studio"
)

$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$excluded = @('.git', '.updates', '__pycache__', 'studio.config.json', 'projects', 'exports', 'models')

New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
Get-ChildItem -LiteralPath $source -Force | Where-Object { $excluded -notcontains $_.Name } | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $InstallRoot -Recurse -Force
}

$launcher = Join-Path $InstallRoot 'Launch YuE Studio.cmd'

Start-Process -FilePath $launcher -WorkingDirectory $InstallRoot
Write-Host "YuE Studio was installed or updated and is opening now."
Write-Host "Installed location: $InstallRoot"
