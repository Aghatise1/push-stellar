@echo off
title Push email delivery setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0configure-email.ps1"
echo.
pause
