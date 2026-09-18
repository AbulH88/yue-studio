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

$launcher = Join-Path $InstallRoot 'launch_yue_studio.cmd'
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = Join-Path $desktop 'YuE Studio.lnk'
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcut)
$link.TargetPath = $launcher
$link.WorkingDirectory = $InstallRoot
$link.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
$link.Description = 'Open YuE Studio'
$link.Save()

Start-Process -FilePath $launcher -WorkingDirectory $InstallRoot
Write-Host "YuE Studio was installed and opened. A desktop shortcut was created at: $shortcut"
