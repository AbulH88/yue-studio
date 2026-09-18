@echo off
setlocal
title Install YuE Studio
echo.
echo  YuE Studio installer
echo  --------------------
echo  This prepares YuE Studio inside this project folder.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_yue_studio.ps1"
set "RESULT=%ERRORLEVEL%"
if "%RESULT%"=="0" (
  echo.
  echo  Installation complete. YuE Studio is opening in your browser.
  echo  Press any key to close this installer window.
  pause >nul
) else (
  echo.
  echo  Installation did not finish. Read the message above, then try again.
  pause
)
endlocal & exit /b %RESULT%
