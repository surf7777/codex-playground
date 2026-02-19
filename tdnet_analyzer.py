#!/usr/bin/env python3
"""
TDnet 適時開示 自動分析システム
================================
毎日16:10に実行し、直近の適時開示から受注・売上関連の開示を
フィルタリングしてExcelレポートを生成する。

データソース:
  1. TDnet公式 日付別一覧ページ (I_list)
  2. TDnet公式 キーワード検索API (TDJFSearch)
"""

import os
import re
import sys
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# ログ設定
# ---------------------------------------------------------------------------
LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
logger = logging.getLogger(__name__)


def setup_file_logging(log_path: Path):
    """ファイルへのログ出力を追加する。"""
    fh = logging.FileHandler(str(log_path), encoding="utf-8", mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(LOG_FMT))
    logging.getLogger().addHandler(fh)
    logger.info("ログファイル: %s", log_path)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
TDNET_BASE = "https://www.release.tdnet.info"
TDNET_LIST_URL = TDNET_BASE + "/inbs/I_list_{page}_{date}.html"
TDNET_SEARCH_URL = TDNET_BASE + "/onsf/TDJFSearch/TDJFSearch"

# フィルタリング対象キーワード群
FILTER_KEYWORDS = {
    "high": [  # 重要度: 高 - 受注関連
        "受注高",
        "受注額",
        "受注残高",
        "手持ち工事高",
        "手持工事高",
        "受注工事高",
        "新規受注",
        "大型受注",
        "受注状況",
        "受注の状況",
        "受注実績",
        "受注についてのお知らせ",
        "受注に関するお知らせ",
        "受注獲得",
        "工事受注",
        "受注見通し",
    ],
    "medium": [  # 重要度: 中 - 売上・業績関連
        "四半期売上",
        "売上高増加",
        "売上増加",
        "増収",
        "売上高の状況",
        "月次売上",
        "売上速報",
        "売上高に関する",
        "売上高の推移",
        "月次情報",
        "月次実績",
        "月次報告",
        "月次速報",
        "業績予想の修正",
        "業績予想の上方修正",
        "通期業績予想の修正",
        "連結業績予想の修正",
        "上方修正",
    ],
}

ALL_KEYWORDS = FILTER_KEYWORDS["high"] + FILTER_KEYWORDS["medium"]

# Excel スタイル
FILL_HIGH = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
FILL_MEDIUM = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
FILL_HEADER = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
FONT_HEADER = Font(name="Meiryo UI", bold=True, color="FFFFFF", size=11)
FONT_NORMAL = Font(name="Meiryo UI", size=10)
FONT_LINK = Font(name="Meiryo UI", size=10, color="0563C1", underline="single")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

# リクエスト設定
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
}
REQUEST_TIMEOUT = 30


# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------
class TDnetFetcher:
    """TDnet から適時開示一覧を取得する。"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(REQUEST_HEADERS)

    def fetch_list_page(self, date_str: str, page: int = 1) -> list[dict]:
        """日付別一覧ページ (I_list) から開示情報を取得する。

        Args:
            date_str: YYYYMMDD 形式の日付文字列
            page: ページ番号 (1-indexed, TDnet上は 001, 002, ...)
        """
        url = TDNET_LIST_URL.format(page=f"{page:03d}", date=date_str)
        logger.info("Fetching: %s", url)

        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.encoding = "utf-8"
        except requests.RequestException as e:
            logger.warning("リスト取得失敗 (%s): %s", url, e)
            return []

        if resp.status_code == 404:
            return []
        resp.raise_for_status()

        return self._parse_list_html(resp.text, date_str)

    def fetch_all_pages_for_date(self, date_str: str) -> list[dict]:
        """指定日の全ページから開示情報を取得する。"""
        all_items = []
        for page in range(1, 20):  # 最大19ページ (1900件) まで
            items = self.fetch_list_page(date_str, page)
            if not items:
                break
            all_items.extend(items)
            logger.info("  ページ %d: %d 件取得", page, len(items))
        return all_items

    def search_by_keyword(self, keyword: str, date_from: str, date_to: str) -> list[dict]:
        """TDnet キーワード検索を使って開示を検索する。

        Args:
            keyword: 検索キーワード
            date_from: 開始日 (YYYYMMDD)
            date_to: 終了日 (YYYYMMDD)
        """
        data = {
            "t0": date_from,
            "t1": date_to,
            "q": keyword,
            "m": "0",
        }
        logger.info("キーワード検索: '%s' (%s - %s)", keyword, date_from, date_to)

        try:
            resp = self.session.post(
                TDNET_SEARCH_URL, data=data, timeout=REQUEST_TIMEOUT
            )
            resp.encoding = "utf-8"
        except requests.RequestException as e:
            logger.warning("検索失敗 (keyword=%s): %s", keyword, e)
            return []

        if resp.status_code != 200:
            logger.warning("検索レスポンス異常: %d", resp.status_code)
            return []

        return self._parse_search_html(resp.text)

    # ------------------------------------------------------------------
    # HTML パーサー
    # ------------------------------------------------------------------
    def _parse_list_html(self, html: str, date_str: str) -> list[dict]:
        """I_list ページの HTML をパースして開示情報のリストを返す。"""
        soup = BeautifulSoup(html, "html.parser")
        items = []

        # テーブル行を取得
        rows = soup.find_all("tr")
        logger.debug("HTML内のtr要素数: %d", len(rows))

        class_based_count = 0
        fallback_count = 0

        for row in rows:
            item = self._extract_row_data(row, date_str)
            if item:
                if item.get("_method") == "class":
                    class_based_count += 1
                else:
                    fallback_count += 1
                item.pop("_method", None)
                items.append(item)

        logger.info(
            "  パース結果: %d 件 (CSSクラス: %d, フォールバック: %d)",
            len(items), class_based_count, fallback_count,
        )
        return items

    def _extract_row_data(self, row, date_str: str) -> dict | None:
        """テーブル行から開示情報を抽出する。"""
        tds = row.find_all("td")
        if len(tds) < 4:
            return None

        # 方式1: CSSクラス名ベースの抽出 (従来方式)
        result = self._extract_by_class(tds, date_str)
        if result and result.get("title"):
            result["_method"] = "class"
            return result

        # 方式2: 列位置ベースのフォールバック抽出
        result = self._extract_by_position(tds, row, date_str)
        if result and result.get("title"):
            result["_method"] = "position"
            return result

        return None

    def _extract_by_class(self, tds, date_str: str) -> dict | None:
        """CSSクラス名ベースで開示情報を抽出する（従来方式）。"""
        time_text = ""
        code_text = ""
        company_name = ""
        title_text = ""
        pdf_url = ""

        for td in tds:
            classes = " ".join(td.get("class", []))

            if "kjTime" in classes:
                time_text = td.get_text(strip=True)
            elif "kjCode" in classes:
                code_text = td.get_text(strip=True)
            elif "kjName" in classes:
                company_name = td.get_text(strip=True)
            elif "kjTitle" in classes:
                title_text = td.get_text(strip=True)
                pdf_url = self._extract_pdf_link(td)

        if not title_text:
            return None

        return {
            "date": date_str,
            "time": time_text,
            "code": code_text,
            "company": company_name,
            "title": title_text,
            "pdf_url": pdf_url,
        }

    def _extract_by_position(self, tds, row, date_str: str) -> dict | None:
        """列位置ベースで開示情報を抽出する（フォールバック）。

        TDnetの一般的なテーブル構造:
          列0: 時刻  列1: コード  列2: 会社名  列3: タイトル  列4: (その他)
        """
        texts = [td.get_text(strip=True) for td in tds]

        # 時刻パターン (HH:MM) を持つ列を探す
        time_col = -1
        for i, t in enumerate(texts):
            if re.match(r"^\d{1,2}:\d{2}$", t):
                time_col = i
                break

        if time_col < 0:
            return None

        # 時刻列の後に コード, 会社名, タイトル が続く想定
        remaining = len(tds) - time_col - 1
        if remaining < 3:
            return None

        code_text = texts[time_col + 1]
        company_name = texts[time_col + 2]

        # タイトル列: リンクを含む列を優先的に探す
        title_text = ""
        pdf_url = ""
        for i in range(time_col + 3, len(tds)):
            link = tds[i].find("a")
            if link:
                title_text = tds[i].get_text(strip=True)
                pdf_url = self._extract_pdf_link(tds[i])
                break
        if not title_text and time_col + 3 < len(tds):
            title_text = texts[time_col + 3]

        if not title_text:
            return None

        # コードが数字っぽいか検証（簡易）
        if not re.match(r"^\d{4}", code_text):
            return None

        return {
            "date": date_str,
            "time": texts[time_col],
            "code": code_text,
            "company": company_name,
            "title": title_text,
            "pdf_url": pdf_url,
        }

    @staticmethod
    def _extract_pdf_link(td) -> str:
        """td要素からPDFリンクを抽出する。"""
        link = td.find("a")
        if link and link.get("href"):
            href = link["href"]
            if href.startswith("/"):
                return TDNET_BASE + href
            elif href.startswith("http"):
                return href
            else:
                return urljoin(TDNET_BASE + "/inbs/", href)
        return ""

    def _parse_search_html(self, html: str) -> list[dict]:
        """キーワード検索結果の HTML をパースする。"""
        soup = BeautifulSoup(html, "html.parser")
        items = []

        rows = soup.find_all("tr")
        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 3:
                continue

            texts = [td.get_text(strip=True) for td in tds]
            link_tag = row.find("a")
            pdf_url = ""
            if link_tag and link_tag.get("href"):
                href = link_tag["href"]
                if href.startswith("http"):
                    pdf_url = href
                elif href.startswith("/"):
                    pdf_url = TDNET_BASE + href

            # 検索結果の列構成を推定して抽出
            # 典型的: 日時 | コード | 会社名 | 表題
            date_time = texts[0] if len(texts) > 0 else ""
            code = texts[1] if len(texts) > 1 else ""
            company = texts[2] if len(texts) > 2 else ""
            title = texts[3] if len(texts) > 3 else (texts[2] if len(texts) > 2 else "")

            # 日時からdate/timeに分割
            date_str = ""
            time_str = ""
            dt_match = re.search(r"(\d{4})[/-]?(\d{2})[/-]?(\d{2})", date_time)
            if dt_match:
                date_str = dt_match.group(1) + dt_match.group(2) + dt_match.group(3)
            tm_match = re.search(r"(\d{1,2}:\d{2})", date_time)
            if tm_match:
                time_str = tm_match.group(1)

            if title:
                items.append({
                    "date": date_str,
                    "time": time_str,
                    "code": code,
                    "company": company,
                    "title": title,
                    "pdf_url": pdf_url,
                })

        return items


# ---------------------------------------------------------------------------
# 分析・フィルタリング
# ---------------------------------------------------------------------------
class DisclosureAnalyzer:
    """取得した開示情報をフィルタリング・分類する。"""

    @staticmethod
    def filter_disclosures(items: list[dict]) -> list[dict]:
        """キーワードに合致する開示のみ抽出し、重要度を付与する。"""
        filtered = []
        seen = set()  # 重複排除用

        for item in items:
            title = item.get("title", "")
            dedup_key = (item.get("code", ""), title, item.get("date", ""))
            if dedup_key in seen:
                continue

            importance = DisclosureAnalyzer._classify_importance(title)
            if importance:
                item["importance"] = importance
                item["matched_keywords"] = DisclosureAnalyzer._find_matched_keywords(title)
                filtered.append(item)
                seen.add(dedup_key)

        # 重要度順 → 日時順にソート
        priority = {"高": 0, "中": 1}
        filtered.sort(key=lambda x: (priority.get(x["importance"], 9), x.get("date", ""), x.get("time", "")))

        return filtered

    @staticmethod
    def _classify_importance(title: str) -> str | None:
        """タイトルからキーワードマッチで重要度を判定する。"""
        for kw in FILTER_KEYWORDS["high"]:
            if kw in title:
                return "高"
        for kw in FILTER_KEYWORDS["medium"]:
            if kw in title:
                return "中"
        return None

    @staticmethod
    def _find_matched_keywords(title: str) -> str:
        """タイトル中に含まれるキーワードを全て列挙する。"""
        matched = []
        for kw in ALL_KEYWORDS:
            if kw in title:
                matched.append(kw)
        return ", ".join(matched)


# ---------------------------------------------------------------------------
# Excel レポート生成
# ---------------------------------------------------------------------------
class ExcelReporter:
    """分析結果を Excel ファイルに出力する。"""

    COLUMNS = [
        ("No.", 5),
        ("重要度", 8),
        ("日付", 12),
        ("時刻", 8),
        ("証券コード", 12),
        ("会社名", 28),
        ("開示タイトル", 55),
        ("マッチキーワード", 28),
        ("PDF URL", 45),
    ]

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, items: list[dict], run_date: datetime,
                 all_items: list[dict] | None = None) -> Path:
        """Excel レポートを生成し、ファイルパスを返す。

        Args:
            items: フィルタリング済みの開示リスト
            run_date: 実行日時
            all_items: 全取得開示リスト (デバッグ用シートに出力)
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "TDnet分析結果"

        self._write_summary_header(ws, run_date, len(items),
                                   total=len(all_items) if all_items else None)
        self._write_table_header(ws, start_row=4)
        self._write_data_rows(ws, items, start_row=5)
        self._apply_formatting(ws, len(items))

        # 全件一覧シート (デバッグ・確認用)
        if all_items:
            self._write_all_items_sheet(wb, all_items)

        filename = f"TDnet分析_{run_date.strftime('%Y%m%d_%H%M')}.xlsx"
        filepath = self.output_dir / filename
        wb.save(str(filepath))
        logger.info("Excel保存: %s", filepath)
        return filepath

    def _write_summary_header(self, ws, run_date: datetime, count: int,
                              total: int | None = None):
        """レポート冒頭のサマリ行を書き込む。"""
        ws.merge_cells("A1:I1")
        cell = ws["A1"]
        cell.value = f"TDnet 適時開示 自動分析レポート - {run_date.strftime('%Y/%m/%d %H:%M')} 実行"
        cell.font = Font(name="Meiryo UI", bold=True, size=14)
        cell.alignment = Alignment(horizontal="center")

        total_info = f"(全{total}件中)" if total is not None else ""
        ws.merge_cells("A2:I2")
        cell2 = ws["A2"]
        cell2.value = (
            f"抽出件数: {count} 件 {total_info}  |  "
            f"対象: 受注・売上・業績修正関連  |  "
            f"凡例: 黄色=重要度 高 / 緑=重要度 中  |  "
            f"※全件一覧は2枚目シート参照"
        )
        cell2.font = Font(name="Meiryo UI", size=10, italic=True)
        cell2.alignment = Alignment(horizontal="center")

    def _write_table_header(self, ws, start_row: int):
        """テーブルヘッダ行を書き込む。"""
        for col_idx, (name, width) in enumerate(self.COLUMNS, 1):
            cell = ws.cell(row=start_row, column=col_idx, value=name)
            cell.font = FONT_HEADER
            cell.fill = FILL_HEADER
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = THIN_BORDER
            ws.column_dimensions[get_column_letter(col_idx)].width = width

    def _write_data_rows(self, ws, items: list[dict], start_row: int):
        """データ行を書き込む。"""
        for i, item in enumerate(items):
            row = start_row + i
            importance = item.get("importance", "")
            fill = FILL_HIGH if importance == "高" else FILL_MEDIUM

            # 日付を整形
            raw_date = item.get("date", "")
            if len(raw_date) == 8:
                formatted_date = f"{raw_date[:4]}/{raw_date[4:6]}/{raw_date[6:8]}"
            else:
                formatted_date = raw_date

            values = [
                i + 1,
                importance,
                formatted_date,
                item.get("time", ""),
                item.get("code", ""),
                item.get("company", ""),
                item.get("title", ""),
                item.get("matched_keywords", ""),
                item.get("pdf_url", ""),  # placeholder; hyperlink set below
            ]

            for col_idx, val in enumerate(values, 1):
                cell = ws.cell(row=row, column=col_idx, value=val)
                cell.font = FONT_NORMAL
                cell.fill = fill
                cell.border = THIN_BORDER
                cell.alignment = Alignment(vertical="center", wrap_text=(col_idx in (7, 8)))

            # PDF URL をクリック可能なハイパーリンクにする
            pdf_url = item.get("pdf_url", "")
            if pdf_url:
                pdf_cell = ws.cell(row=row, column=9)
                pdf_cell.hyperlink = pdf_url
                pdf_cell.value = pdf_url
                pdf_cell.font = FONT_LINK
                pdf_cell.fill = fill

    def _apply_formatting(self, ws, data_count: int):
        """全体的なフォーマット調整。"""
        # 行の高さ
        ws.row_dimensions[1].height = 30
        ws.row_dimensions[2].height = 20
        ws.row_dimensions[4].height = 25
        for r in range(5, 5 + data_count):
            ws.row_dimensions[r].height = 22

        # フィルター設定
        if data_count > 0:
            last_col = get_column_letter(len(self.COLUMNS))
            ws.auto_filter.ref = f"A4:{last_col}{4 + data_count}"

        # 印刷設定
        ws.sheet_properties.pageSetUpPr = None
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

    def _write_all_items_sheet(self, wb: Workbook, all_items: list[dict]):
        """全件一覧シートを書き込む (取得結果の確認・デバッグ用)。"""
        ws = wb.create_sheet(title="全件一覧")

        # ヘッダ
        headers = [("No.", 5), ("日付", 12), ("時刻", 8), ("証券コード", 12),
                   ("会社名", 28), ("開示タイトル", 60), ("PDF URL", 45)]
        for col_idx, (name, width) in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=name)
            cell.font = FONT_HEADER
            cell.fill = FILL_HEADER
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = THIN_BORDER
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # 重複排除
        seen = set()
        unique_items = []
        for item in all_items:
            key = (item.get("code", ""), item.get("title", ""), item.get("date", ""))
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        # データ行
        for i, item in enumerate(unique_items):
            row = i + 2
            raw_date = item.get("date", "")
            if len(raw_date) == 8:
                formatted_date = f"{raw_date[:4]}/{raw_date[4:6]}/{raw_date[6:8]}"
            else:
                formatted_date = raw_date

            values = [
                i + 1,
                formatted_date,
                item.get("time", ""),
                item.get("code", ""),
                item.get("company", ""),
                item.get("title", ""),
                item.get("pdf_url", ""),
            ]
            for col_idx, val in enumerate(values, 1):
                cell = ws.cell(row=row, column=col_idx, value=val)
                cell.font = FONT_NORMAL
                cell.border = THIN_BORDER

            # PDF URL をハイパーリンクにする
            pdf_url = item.get("pdf_url", "")
            if pdf_url:
                pdf_cell = ws.cell(row=row, column=7)
                pdf_cell.hyperlink = pdf_url
                pdf_cell.font = FONT_LINK

        # フィルター設定
        if unique_items:
            last_col = get_column_letter(len(headers))
            ws.auto_filter.ref = f"A1:{last_col}{len(unique_items) + 1}"

        logger.info("全件一覧シート: %d 件 (重複排除後)", len(unique_items))


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------
def get_default_output_dir() -> Path:
    """デフォルトの出力先ディレクトリを返す。

    Windows の OneDrive フォルダリダイレクト環境にも対応する。
    """
    home = Path.home()

    if sys.platform == "win32":
        # OneDrive でリダイレクトされている場合の候補パス
        candidates = [
            home / "OneDrive" / "ドキュメント",
            home / "OneDrive" / "Documents",
            home / "OneDrive - Personal" / "Documents",
            home / "OneDrive - Personal" / "ドキュメント",
            home / "Documents",
        ]
        for cand in candidates:
            if cand.exists():
                logger.info("ドキュメントフォルダ検出: %s", cand)
                return cand / "TDnet分析結果"
        # どれも見つからない場合はスクリプト配置場所に出力
        logger.warning("Documents フォルダが見つかりません。スクリプトと同じ場所に出力します。")
        return Path(__file__).parent / "TDnet分析結果"
    else:
        docs = home / "Documents"
        return docs / "TDnet分析結果"


def collect_disclosures(fetcher: TDnetFetcher, target_dates: list[str]) -> list[dict]:
    """複数手法で適時開示を収集する。"""
    all_items = []

    # 方式1: 日付別一覧ページから全件取得
    for date_str in target_dates:
        logger.info("=== 日付別一覧取得: %s ===", date_str)
        items = fetcher.fetch_all_pages_for_date(date_str)
        all_items.extend(items)
        logger.info("  合計 %d 件", len(items))

    # 方式2: キーワード検索で補完 (一覧で漏れがある場合の対策)
    if len(target_dates) >= 1:
        date_from = target_dates[0]
        date_to = target_dates[-1]
        search_keywords = ["受注高", "受注残高", "手持ち工事高", "売上増加"]
        for kw in search_keywords:
            logger.info("=== キーワード検索: %s ===", kw)
            items = fetcher.search_by_keyword(kw, date_from, date_to)
            all_items.extend(items)
            logger.info("  %d 件", len(items))

    logger.info("収集合計: %d 件 (重複含む)", len(all_items))
    return all_items


def main():
    parser = argparse.ArgumentParser(
        description="TDnet 適時開示 自動分析システム"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="対象日 (YYYYMMDD)。省略時は本日+前営業日",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="遡る日数 (デフォルト: 1 = 直近24時間)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Excel 出力先ディレクトリ",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="取得・分析のみ行い Excel を生成しない",
    )
    args = parser.parse_args()

    now = datetime.now()

    # ファイルログを設定 (スクリプトと同じ場所に出力)
    log_path = Path(__file__).parent / "run_log.txt"
    setup_file_logging(log_path)

    logger.info("TDnet 適時開示 自動分析システム 開始: %s", now.strftime("%Y/%m/%d %H:%M:%S"))

    # 対象日の決定
    if args.date:
        target_dates = [args.date]
    else:
        target_dates = []
        for d in range(args.days + 1):
            dt = now - timedelta(days=d)
            target_dates.append(dt.strftime("%Y%m%d"))

    logger.info("対象日: %s", ", ".join(target_dates))

    # 出力先
    output_dir = Path(args.output_dir) if args.output_dir else get_default_output_dir()

    # データ収集
    fetcher = TDnetFetcher()
    raw_items = collect_disclosures(fetcher, target_dates)

    # 重複排除して全件数を確認
    seen_all = set()
    unique_raw = []
    for item in raw_items:
        key = (item.get("code", ""), item.get("title", ""), item.get("date", ""))
        if key not in seen_all:
            seen_all.add(key)
            unique_raw.append(item)

    logger.info("=" * 60)
    logger.info("取得合計: %d 件 (重複排除後: %d 件)", len(raw_items), len(unique_raw))

    # フィルタリング・分析
    analyzer = DisclosureAnalyzer()
    filtered = analyzer.filter_disclosures(raw_items)

    logger.info("フィルタリング結果: %d 件 / %d 件中", len(filtered), len(unique_raw))
    for item in filtered:
        logger.info(
            "  [%s] %s %s - %s",
            item["importance"],
            item.get("code", ""),
            item.get("company", ""),
            item.get("title", ""),
        )

    # コンソールにもサマリを表示 (bat ファイルで見やすいように)
    print()
    print("=" * 50)
    print(f"  TDnet取得結果サマリ")
    print(f"  対象日: {', '.join(target_dates)}")
    print(f"  取得件数: {len(unique_raw)} 件")
    print(f"  フィルタ後: {len(filtered)} 件")
    if not unique_raw:
        print()
        print("  ※ 取得件数が0件です！")
        print("    TDnetのHTML構造が変更された可能性があります。")
        print("    run_log.txt を確認してください。")
    print("=" * 50)
    print()

    if args.dry_run:
        logger.info("ドライラン完了。Excel は生成しません。")
        return

    # Excel レポート生成 (全件一覧シート付き)
    reporter = ExcelReporter(output_dir)
    filepath = reporter.generate(filtered, now, all_items=raw_items)
    logger.info("レポート生成完了: %s", filepath)
    print(f"  Excelファイル: {filepath}")

    logger.info("TDnet 適時開示 自動分析システム 完了")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("予期しないエラーが発生しました: %s", e, exc_info=True)
        print(f"\n*** エラー: {e} ***\n", file=sys.stderr)
        sys.exit(1)
