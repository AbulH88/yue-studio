@echo off
setlocal
title Install YuE Studio
echo.
echo  YuE Studio installer
echo  --------------------
echo  This installs or safely updates YuE Studio for this Windows account.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_yue_studio.ps1"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo.
  echo  Installation did not finish. Read the message above, then try again.
  pause
)
endlocal & exit /b %RESULT%
