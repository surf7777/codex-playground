@echo off
chcp 65001 >nul

echo ============================================================
echo  TDnet Task Scheduler Setup
echo ============================================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Run as administrator.
    pause
    exit /b 1
)

set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo Install dir: %SCRIPT_DIR%
echo.

set TASK_NAME=TDnet_AutoAnalysis

schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Deleting existing task...
    schtasks /delete /tn "%TASK_NAME%" /f
)

echo Registering task...
schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_DIR%\run_analysis.bat\"" /sc daily /st 16:10 /rl HIGHEST /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo  Setup Complete!
    echo ============================================================
    echo  Task:     %TASK_NAME%
    echo  Schedule: Daily 16:10
    echo  Script:   %SCRIPT_DIR%\run_analysis.bat
    echo ============================================================
) else (
    echo.
    echo [ERROR] Failed to register task.
)

echo.
pause
