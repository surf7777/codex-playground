@echo off
chcp 65001 >nul
REM ============================================================
REM TDnet Auto Analysis - 初回セットアップ
REM ============================================================

cd /d "%~dp0"

echo.
echo ========================================
echo  TDnet 適時開示 自動分析システム
echo  初回セットアップを開始します
echo ========================================
echo.

REM Step 1: Check Python
echo [1/3] Python を確認中...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ★ Python がインストールされていません！
    echo.
    echo   以下の手順で Python をインストールしてください:
    echo   1. https://www.python.org/downloads/ を開く
    echo   2. 「Download Python」ボタンをクリック
    echo   3. インストーラーを実行
    echo   4. ★重要★「Add Python to PATH」にチェックを入れる
    echo   5. 「Install Now」をクリック
    echo   6. インストール完了後、もう一度この setup を実行
    echo.
    echo   今すぐダウンロードページを開きますか？
    choice /c YN /m "  (Y=はい / N=いいえ)"
    if %ERRORLEVEL% EQU 1 (
        start https://www.python.org/downloads/
    )
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo   OK: %PYVER%

REM Step 2: Create virtual environment
echo.
echo [2/3] 仮想環境を作成中...
if exist "venv\Scripts\python.exe" (
    echo   既に存在します（スキップ）
) else (
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo   仮想環境の作成に失敗しました
        pause
        exit /b 1
    )
    echo   OK: 仮想環境を作成しました
)

REM Step 3: Install packages
echo.
echo [3/3] 必要なパッケージをインストール中...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo   パッケージのインストールに失敗しました
    pause
    exit /b 1
)
echo   OK: パッケージをインストールしました

echo.
echo ========================================
echo  セットアップ完了！
echo.
echo  次のステップ:
echo  「run_analysis」をダブルクリック
echo  → TDnet から開示情報を取得して
echo     Excel レポートが生成されます
echo ========================================
echo.
pause
