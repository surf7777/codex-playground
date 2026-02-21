#!/usr/bin/env python3
"""TDnet 適時開示データ 日次自動抽出スクリプト

毎日 TDnet から適時開示情報を取得し、Claude API でスコアリングして
個人投資家にとって重要度の高い開示を TSV ファイルに出力する。

出力形式 (TSV):
  時刻 | コード | 会社名 | タイトル | スコア | 理由

使い方:
  # 当日の開示を取得
  python src/main.py

  # 特定日の開示を取得
  python src/main.py --date 2026-02-20

  # スコア閾値を変更 (デフォルト: 3)
  python src/main.py --min-score 4

環境変数:
  ANTHROPIC_API_KEY: Claude API キー (必須)
"""

import argparse
import csv
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# src ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper import scrape_all_pages
from scorer import score_disclosures

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# プロジェクトルートの data ディレクトリ
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TDnet 適時開示日次抽出")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="対象日 (YYYY-MM-DD 形式, デフォルト: 当日)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=3,
        help="出力する最低スコア (デフォルト: 3)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="出力ディレクトリ (デフォルト: data/)",
    )
    return parser.parse_args()


def get_target_date(date_str: str | None) -> date:
    """対象日を取得。指定なしの場合は当日(平日)を返す"""
    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    return date.today()


def write_tsv(scored_disclosures, output_path: Path) -> None:
    """スコア付き開示情報を TSV に出力する"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["時刻", "コード", "会社名", "タイトル", "スコア", "理由"])
        for d in scored_disclosures:
            writer.writerow([d.time, d.code, d.company, d.title, d.score, d.reason])

    logger.info("Output written to %s (%d rows)", output_path, len(scored_disclosures))


def write_summary(scored_disclosures, target_date: date, output_dir: Path) -> None:
    """日次サマリーをテキストファイルに出力"""
    summary_path = output_dir / f"summary_{target_date.strftime('%Y%m%d')}.txt"

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"=== TDnet 適時開示サマリー {target_date.strftime('%Y/%m/%d')} ===\n\n")

        if not scored_disclosures:
            f.write("該当する開示情報はありませんでした。\n")
            return

        # スコア別集計
        score_counts = {}
        for d in scored_disclosures:
            score_counts[d.score] = score_counts.get(d.score, 0) + 1

        f.write(f"抽出件数: {len(scored_disclosures)} 件\n")
        for score in sorted(score_counts.keys(), reverse=True):
            f.write(f"  スコア {score}: {score_counts[score]} 件\n")
        f.write("\n")

        # スコア5の注目銘柄
        high_score = [d for d in scored_disclosures if d.score >= 5]
        if high_score:
            f.write("【最注目】スコア5\n")
            for d in high_score:
                f.write(f"  {d.code} {d.company}: {d.title}\n")
                f.write(f"    → {d.reason}\n")
            f.write("\n")

        # スコア4
        score4 = [d for d in scored_disclosures if d.score == 4]
        if score4:
            f.write("【注目】スコア4\n")
            for d in score4:
                f.write(f"  {d.code} {d.company}: {d.title}\n")
                f.write(f"    → {d.reason}\n")
            f.write("\n")

    logger.info("Summary written to %s", summary_path)


def main() -> None:
    args = parse_args()

    # API キーの確認
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable is not set")
        sys.exit(1)

    target_date = get_target_date(args.date)
    output_dir = Path(args.output_dir) if args.output_dir else DATA_DIR
    output_path = output_dir / f"tdnet_filtered_scored_{target_date.strftime('%Y%m%d')}.tsv"

    logger.info("=== TDnet 日次抽出開始 ===")
    logger.info("対象日: %s", target_date)
    logger.info("最低スコア: %d", args.min_score)
    logger.info("出力先: %s", output_path)

    # 1. TDnet から開示情報を取得
    logger.info("Step 1: TDnet からデータ取得中...")
    disclosures = scrape_all_pages(target_date)

    if not disclosures:
        logger.warning("開示情報が見つかりませんでした (休日の可能性があります)")
        # 空の TSV を出力
        write_tsv([], output_path)
        return

    logger.info("取得件数: %d 件", len(disclosures))

    # 2. Claude API でスコアリング
    logger.info("Step 2: Claude API でスコアリング中...")
    scored = score_disclosures(disclosures, min_score=args.min_score)

    # 3. TSV に出力
    logger.info("Step 3: 結果出力中...")
    write_tsv(scored, output_path)

    # 4. サマリー出力
    write_summary(scored, target_date, output_dir)

    logger.info("=== 完了: %d 件抽出 ===", len(scored))


if __name__ == "__main__":
    main()
