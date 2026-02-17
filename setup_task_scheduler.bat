@echo off
chcp 65001 >nul
REM ============================================================
REM TDnet - Task Scheduler Setup
REM Run as Administrator
REM ============================================================

echo ============================================================
echo  TDnet Task Scheduler Setup
echo ============================================================
echo.

REM Admin check
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Administrator privileges required.
    echo Right-click and select "Run as administrator".
    pause
    exit /b 1
)

REM Get script directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo Install dir: %SCRIPT_DIR%
echo.

REM Task name (ASCII only to avoid encoding issues)
set TASK_NAME=TDnet_AutoAnalysis

REM Delete existing task if exists
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Deleting existing task...
    schtasks /delete /tn "%TASK_NAME%" /f
)

REM Create task - runs daily at 16:10
echo Registering task scheduler...
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%SCRIPT_DIR%\run_analysis.bat\"" ^
    /sc daily ^
    /st 16:10 ^
    /rl HIGHEST ^
    /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo  Setup Complete!
    echo ============================================================
    echo  Task:     %TASK_NAME%
    echo  Schedule: Daily 16:10
    echo  Script:   %SCRIPT_DIR%\run_analysis.bat
    echo  Output:   %%USERPROFILE%%\Documents\TDnet分析結果\
    echo ============================================================
) else (
    echo.
    echo [ERROR] Failed to register task.
)

echo.
pause
