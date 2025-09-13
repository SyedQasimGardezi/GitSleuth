@echo off
echo Starting GitSleuth Backend...

REM --- Prefer py if available, else python ---
where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON=py
) else (
    set PYTHON=python
)

REM --- Activate virtual environment ---
call backend\venv\Scripts\activate.bat

REM --- Change to backend directory ---
cd backend

REM --- Start the backend ---
%PYTHON% main.py

pause
