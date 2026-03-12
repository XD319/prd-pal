@echo off
setlocal
set ROOT=%~dp0
set FRONTEND_URL=http://127.0.0.1:5173/

echo [MARRDP] Opening frontend dev server in a new window...
start "MARRDP Frontend" cmd /k ""%ROOT%start-frontend-dev.cmd""

echo [MARRDP] Waiting briefly before opening the browser...
timeout /t 5 /nobreak >nul
start "" "%FRONTEND_URL%"

echo [MARRDP] Starting backend in this window. Keep this window open while using the app.
title MARRDP Backend
call "%ROOT%start-backend-dev.cmd"
