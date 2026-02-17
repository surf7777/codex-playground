@echo off
REM ============================================================
REM TDnet 適時開示 自動分析 - タスクスケジューラ登録スクリプト
REM 管理者権限で実行してください
REM ============================================================

echo ============================================================
echo  TDnet 適時開示 自動分析 - タスクスケジューラ セットアップ
echo ============================================================
echo.

REM 管理者権限チェック
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [エラー] 管理者権限が必要です。
    echo 右クリック → 「管理者として実行」で再実行してください。
    pause
    exit /b 1
)

REM スクリプトのディレクトリを取得
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo インストール先: %SCRIPT_DIR%
echo.

REM タスク名
set TASK_NAME=TDnet_適時開示_自動分析

REM 既存タスクの削除（存在する場合）
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo 既存のタスクを削除します...
    schtasks /delete /tn "%TASK_NAME%" /f
)

REM タスクの作成
REM 毎日16:10に実行、ログオン中でなくても実行
echo タスクスケジューラに登録します...
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
    echo  セットアップ完了
    echo ============================================================
    echo  タスク名:   %TASK_NAME%
    echo  実行時刻:   毎日 16:10
    echo  実行内容:   %SCRIPT_DIR%\run_analysis.bat
    echo  出力先:     %%USERPROFILE%%\Documents\TDnet分析結果\
    echo ============================================================
) else (
    echo.
    echo [エラー] タスクの登録に失敗しました。
)

echo.
pause
