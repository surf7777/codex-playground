@echo off
chcp 65001 >nul
REM ============================================================
REM TDnet Auto Analysis - Run Script
REM ============================================================

cd /d "%~dp0"

REM Activate Python virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run analysis
python tdnet_analyzer.py --days 1

REM Keep exit code
set EXITCODE=%ERRORLEVEL%

REM Deactivate virtual environment
if exist "venv\Scripts\deactivate.bat" (
    call deactivate
)

exit /b %EXITCODE%
