# TDnet 適時開示 日次自動抽出ツール

TDnet（適時開示情報閲覧サービス）から毎日自動で開示情報を取得し、Claude API で個人投資家目線のスコアリング（1〜5）を行い、注目度の高い開示をTSVファイルに出力するツール。

## 出力形式

`data/tdnet_filtered_scored_YYYYMMDD.tsv`:

| 時刻 | コード | 会社名 | タイトル | スコア | 理由 |
|------|--------|--------|----------|--------|------|
| 15:00 | 7203 | トヨタ自動車 | 業績予想の修正に関するお知らせ | 5 | 大幅な業績上方修正 |

## セットアップ

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
```

## 使い方

```bash
# 当日の開示を取得・スコアリング
python src/main.py

# 特定日を指定
python src/main.py --date 2026-02-20

# スコア閾値を変更 (デフォルト: 3)
python src/main.py --min-score 4
```

## スコア基準

| スコア | 意味 | 例 |
|--------|------|-----|
| 5 | 株価に大きなインパクト | 大幅業績修正、大型M&A、MBO、株式分割 |
| 4 | 相当のインパクト | 中程度の業績修正、資本業務提携、増配 |
| 3 | 注目すべき情報 | 決算短信、株主優待変更、新製品発表 |
| 2 | 一般的な開示 | 定時株主総会招集、コーポレートガバナンス報告 |
| 1 | 定型的な開示 | 定款変更、組織変更 |

## GitHub Actions (自動実行)

毎週月〜金 JST 18:00 に自動実行されます。手動実行も可能です。

### 必要な設定

1. リポジトリの Settings > Secrets and variables > Actions で `ANTHROPIC_API_KEY` を設定
2. Actions タブで手動実行（Run workflow）も可能

## プロジェクト構成

```
├── src/
│   ├── main.py        # メインスクリプト
│   ├── scraper.py     # TDnet スクレイピング
│   └── scorer.py      # Claude API スコアリング
├── data/              # 出力データ (TSV)
├── .github/workflows/
│   └── daily-tdnet.yml  # GitHub Actions ワークフロー
└── requirements.txt
```
