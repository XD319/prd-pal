@echo off
setlocal
set ROOT=%~dp0
set FRONTEND_URL=http://127.0.0.1:5173/

echo [PRD-Pal] Opening frontend dev server in a new window...
start "PRD-Pal Frontend" cmd /k ""%ROOT%start-frontend-dev.cmd""

echo [PRD-Pal] Waiting briefly before opening the browser...
timeout /t 5 /nobreak >nul
start "" "%FRONTEND_URL%"

echo [PRD-Pal] Starting backend in this window. Keep this window open while using the app.
title PRD-Pal Backend
call "%ROOT%start-backend-dev.cmd"
