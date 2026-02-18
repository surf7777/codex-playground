@echo off
chcp 65001 >nul
REM ============================================================
REM TDnet Auto Analysis - Run Script
REM ============================================================

cd /d "%~dp0"

REM Check if setup has been done
if not exist "venv\Scripts\python.exe" (
    echo.
    echo ========================================
    echo  初回セットアップが必要です！
    echo  先に「setup」をダブルクリックしてください
    echo ========================================
    echo.
    pause
    exit /b 1
)

REM Activate Python virtual environment
call venv\Scripts\activate.bat

REM Run analysis
echo.
echo TDnet 適時開示 自動分析を実行中...
echo.
python tdnet_analyzer.py --days 1

REM Keep exit code
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% EQU 0 (
    echo.
    echo ========================================
    echo  完了！Excelファイルが生成されました
    echo  保存先: ドキュメント\TDnet分析結果\
    echo ========================================
) else (
    echo.
    echo ========================================
    echo  エラーが発生しました（コード: %EXITCODE%）
    echo ========================================
)

echo.
pause
exit /b %EXITCODE%
