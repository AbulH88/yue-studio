@echo off
setlocal
set "APP_ROOT=%~dp0"
set "APP_URL=http://127.0.0.1:8765"

curl.exe --silent --max-time 1 "%APP_URL%/api/config" >nul 2>nul
if not errorlevel 1 goto open_browser

if exist "%APP_ROOT%.updates\pending-update.json" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%APP_ROOT%apply_pending_update.ps1" -InstallRoot "%APP_ROOT%"
)

where py >nul 2>nul
if not errorlevel 1 (
  start "YuE Studio" /B py -3 "%APP_ROOT%yue_studio\app.py"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo YuE Studio needs Python 3.10 or newer. Reinstall YuE Studio or install Python from python.org.
    pause
    exit /b 1
  )
  start "YuE Studio" /B python "%APP_ROOT%yue_studio\app.py"
)

:wait_for_app
timeout /t 1 /nobreak >nul
curl.exe --silent --max-time 1 "%APP_URL%/api/config" >nul 2>nul
if errorlevel 1 goto wait_for_app

:open_browser
start "" "%APP_URL%"
endlocal
