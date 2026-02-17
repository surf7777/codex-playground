# TDnet 適時開示 自動分析システム - セットアップガイド

## 概要

TDnet（適時開示情報閲覧サービス）から毎日自動で開示情報を取得し、
受注・売上関連の開示をフィルタリングしてExcelレポートを生成するシステムです。

### フィルタリング対象

| 重要度 | キーワード |
|--------|-----------|
| 高（黄色）| 受注高、受注額、受注残高、手持ち工事高、新規受注、大型受注、受注状況 |
| 中（緑） | 四半期売上、売上高増加、増収、売上高の状況、月次売上、売上速報 |

---

## 前提条件

- Windows 10/11
- Python 3.11 以上（3.10でも動作可能）
- インターネット接続

---

## セットアップ手順

### 1. Python のインストール

Python が未インストールの場合:

1. https://www.python.org/downloads/ からインストーラーをダウンロード
2. インストール時に **「Add Python to PATH」にチェック** を入れる
3. インストール完了後、コマンドプロンプトで確認:

```cmd
python --version
```

### 2. プロジェクトの配置

任意のフォルダにプロジェクトファイルを配置します（例: `C:\Tools\TDnetAnalyzer\`）。

必要なファイル:
```
C:\Tools\TDnetAnalyzer\
├── tdnet_analyzer.py          # メインスクリプト
├── requirements.txt           # 依存パッケージ
├── run_analysis.bat           # 実行用バッチ
└── setup_task_scheduler.bat   # タスクスケジューラ登録用
```

### 3. 仮想環境の作成と依存パッケージのインストール

コマンドプロンプトで以下を実行:

```cmd
cd C:\Tools\TDnetAnalyzer

REM 仮想環境の作成
python -m venv venv

REM 仮想環境の有効化
venv\Scripts\activate

REM 依存パッケージのインストール
pip install -r requirements.txt
```

### 4. 動作確認（手動実行）

```cmd
REM 仮想環境を有効化した状態で実行
python tdnet_analyzer.py --days 1
```

成功すると `%USERPROFILE%\Documents\TDnet分析結果\` に Excel ファイルが生成されます。

### 5. タスクスケジューラへの登録

`setup_task_scheduler.bat` を **右クリック → 「管理者として実行」** します。

これにより毎日 16:10 に自動実行されるタスクが登録されます。

---

## コマンドラインオプション

```
python tdnet_analyzer.py [オプション]

オプション:
  --date YYYYMMDD    特定の日付のみ分析
  --days N           遡る日数（デフォルト: 1）
  --output-dir PATH  Excel出力先の変更
  --dry-run          取得・分析のみ実行（Excel生成なし）
```

### 使用例

```cmd
REM 本日＋昨日の開示を分析（デフォルト動作）
python tdnet_analyzer.py

REM 特定日の開示を分析
python tdnet_analyzer.py --date 20260216

REM 過去3日分を分析
python tdnet_analyzer.py --days 3

REM 出力先を変更
python tdnet_analyzer.py --output-dir "D:\Reports\TDnet"

REM ドライラン（Excel生成なし、ログで確認のみ）
python tdnet_analyzer.py --dry-run
```

---

## 出力ファイル

### 保存先

```
%USERPROFILE%\Documents\TDnet分析結果\TDnet分析_YYYYMMDD_HHMM.xlsx
```

### Excel の内容

| 列 | 内容 |
|----|------|
| No. | 連番 |
| 重要度 | 高 / 中 |
| 日付 | 開示日 |
| 時刻 | 開示時刻 |
| 証券コード | 上場企業コード |
| 会社名 | 企業名 |
| 開示タイトル | 適時開示の表題 |
| マッチキーワード | 検出されたキーワード |
| PDF URL | クリックで開示PDFを直接開ける |

### 色分け

- **黄色**: 重要度「高」（受注高・受注額・受注残高・手持ち工事高 など）
- **緑色**: 重要度「中」（四半期売上・増収 など）

---

## タスクスケジューラの確認・変更

### 確認方法

```cmd
schtasks /query /tn "TDnet_適時開示_自動分析" /v
```

### 実行時刻の変更

```cmd
schtasks /change /tn "TDnet_適時開示_自動分析" /st 17:00
```

### タスクの削除

```cmd
schtasks /delete /tn "TDnet_適時開示_自動分析" /f
```

### 手動でタスクを即時実行

```cmd
schtasks /run /tn "TDnet_適時開示_自動分析"
```

---

## トラブルシューティング

### Excel が生成されない

1. コマンドプロンプトで手動実行してエラーを確認:
   ```cmd
   cd C:\Tools\TDnetAnalyzer
   venv\Scripts\activate
   python tdnet_analyzer.py --days 1
   ```

2. 出力先ディレクトリが存在するか確認（初回は自動作成されます）

### TDnet に接続できない

- インターネット接続を確認
- プロキシ環境の場合、環境変数 `HTTP_PROXY` / `HTTPS_PROXY` を設定
- TDnet がメンテナンス中の可能性（土日祝は開示なし）

### 結果が0件

- 土日祝日は適時開示がないため正常動作です
- `--dry-run` で取得状況をログから確認してください

---

## データソースについて

本システムは以下の2つの方法で TDnet から開示情報を取得します:

1. **日付別一覧ページ** (`I_list_001_YYYYMMDD.html`) - 全件取得してフィルタリング
2. **キーワード検索** (`TDJFSearch`) - 受注・売上関連キーワードで直接検索

両方の結果を統合し、重複を排除して最終レポートを生成します。
