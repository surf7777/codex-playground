@echo off
chcp 65001 >nul 2>&1
REM ============================================================
REM TDnet Auto Analysis - Run Script
REM ============================================================

cd /d "%~dp0"

REM Log file for debugging
set LOGFILE=%~dp0run_log.txt
echo ======================================== > "%LOGFILE%"
echo [%date% %time%] Starting run_analysis... >> "%LOGFILE%"
echo ======================================== >> "%LOGFILE%"

REM Check if setup has been done
if not exist "venv\Scripts\python.exe" (
    echo.
    echo ========================================
    echo  Setup has not been done!
    echo  Please double-click [setup] first.
    echo ========================================
    echo.
    echo [%date% %time%] ERROR: venv not found >> "%LOGFILE%"
    pause
    exit /b 1
)

echo [%date% %time%] venv found OK >> "%LOGFILE%"

REM Activate Python virtual environment
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate virtual environment
    echo [%date% %time%] ERROR: activate.bat failed >> "%LOGFILE%"
    pause
    exit /b 1
)
echo [%date% %time%] venv activated >> "%LOGFILE%"

REM Run analysis (show output on screen AND save to log)
echo.
echo TDnet Analysis is running...
echo Please wait...
echo.
echo [%date% %time%] Running: python tdnet_analyzer.py --days 1 >> "%LOGFILE%"
echo ---- Python output start ---- >> "%LOGFILE%"

python tdnet_analyzer.py --days 1 >> "%LOGFILE%" 2>&1
set EXITCODE=%ERRORLEVEL%

echo ---- Python output end ---- >> "%LOGFILE%"
echo [%date% %time%] Python exit code: %EXITCODE% >> "%LOGFILE%"

REM Show log contents to user
echo.
echo === Log output ===
type "%LOGFILE%"
echo.

if %EXITCODE% EQU 0 (
    echo ========================================
    echo  Done! Check Documents folder for Excel.
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
