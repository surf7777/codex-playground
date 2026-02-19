@echo off
chcp 65001 >nul 2>&1
REM ============================================================
REM TDnet Auto Analysis - Run Script
REM ============================================================

cd /d "%~dp0"

REM Check if setup has been done
if not exist "venv\Scripts\python.exe" (
    echo.
    echo ========================================
    echo  Setup has not been done!
    echo  Please double-click [setup] first.
    echo ========================================
    echo.
    pause
    exit /b 1
)

REM Activate Python virtual environment
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Run analysis (stdout to screen, logs to run_log.txt via Python)
echo.
echo TDnet Analysis is running...
echo Please wait...
echo.

python tdnet_analyzer.py --days 1
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% EQU 0 (
    echo ========================================
    echo  Done! Check Documents folder for Excel.
    echo  Details: run_log.txt
    echo ========================================
) else (
    echo ========================================
    echo  Error occurred. Code: %EXITCODE%
    echo  Details saved to: run_log.txt
    echo ========================================
)

echo.
echo Press any key to close this window...
pause >nul
exit /b %EXITCODE%
