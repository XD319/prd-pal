@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

if exist "%ROOT%\.venv\Scripts\python.exe" (
  "%ROOT%\.venv\Scripts\python.exe" main.py
  exit /b %errorlevel%
)

if exist "%ROOT%\venv\Scripts\python.exe" (
  "%ROOT%\venv\Scripts\python.exe" main.py
  exit /b %errorlevel%
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 main.py
  exit /b %errorlevel%
)

python main.py
