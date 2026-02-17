@echo off
REM ============================================================
REM TDnet 適時開示 自動分析 - 実行バッチファイル
REM Windowsタスクスケジューラから呼び出される
REM ============================================================

cd /d "%~dp0"

REM Python仮想環境を使用する場合
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 分析実行
python tdnet_analyzer.py --days 1

REM 終了コードを保持
set EXITCODE=%ERRORLEVEL%

REM 仮想環境を無効化
if exist "venv\Scripts\deactivate.bat" (
    call deactivate
)

exit /b %EXITCODE%
