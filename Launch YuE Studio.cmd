@echo off
setlocal
title YuE Studio Launcher
set "APP_ROOT=%~dp0"
set "APP_URL=http://127.0.0.1:8765"

curl.exe --silent --max-time 1 "%APP_URL%/api/config" >nul 2>nul
if not errorlevel 1 goto existing_server

if exist "%APP_ROOT%.updates\pending-update.json" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%APP_ROOT%apply_pending_update.ps1" -InstallRoot "%APP_ROOT%"
)

where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo YuE Studio needs Python 3.10 or newer. Run "Install YuE Studio.cmd" first.
    pause
    exit /b 1
  )
  set "PYTHON=python"
)

echo.
echo  Starting YuE Studio...
echo  Your browser will open when Studio is ready.
echo  Press Ctrl+C in this window to stop YuE Studio.
echo.
start "YuE Studio Browser" /B powershell.exe -NoProfile -WindowStyle Hidden -Command "$deadline = (Get-Date).AddSeconds(30); while ((Get-Date) -lt $deadline) { try { Invoke-WebRequest -UseBasicParsing '%APP_URL%/api/config' -TimeoutSec 1 ^| Out-Null; Start-Process '%APP_URL%'; exit 0 } catch { Start-Sleep -Seconds 1 } }"
call %PYTHON% "%APP_ROOT%yue_studio\app.py"

echo.
echo  YuE Studio has stopped.
pause
endlocal
exit /b 0

:existing_server
echo.
echo  YuE Studio is already running in another launcher window.
echo  This window cannot stop that existing server.
start "" "%APP_URL%"
pause
endlocal
exit /b 0
