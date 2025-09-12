@echo off
echo Starting GitSleuth Backend...

REM --- Prefer py if available, else python ---
where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON=py
) else (
    set PYTHON=python
)

cd backend
%PYTHON% main.py

pause
