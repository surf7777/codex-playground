"""TDnet 適時開示情報スクレイピングモジュール

TDnet の適時開示一覧ページから開示情報を取得する。
URL パターン: https://www.release.tdnet.info/inbs/I_list_001_YYYYMMDD.html
"""

import re
import time
import logging
from dataclasses import dataclass
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.release.tdnet.info/inbs/I_list_{page:03d}_{date}.html"

# TDnet のテーブルから抽出する際の正規表現
CODE_PATTERN = re.compile(r"^(\d{4,5})")


@dataclass
class Disclosure:
    """適時開示情報 1 件分のデータ"""

    time: str  # 開示時刻 (例: "15:00")
    code: str  # 証券コード (例: "7203")
    company: str  # 会社名 (例: "トヨタ自動車")
    title: str  # 開示タイトル
    pdf_url: str  # PDF の URL


def fetch_page(target_date: date, page: int = 1) -> str:
    """TDnet の適時開示一覧ページの HTML を取得する"""
    url = BASE_URL.format(page=page, date=target_date.strftime("%Y%m%d"))
    logger.info("Fetching: %s", url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    for attempt in range(4):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text
        except requests.RequestException as e:
            wait = 2 ** (attempt + 1)
            logger.warning("Attempt %d failed: %s. Retrying in %ds...", attempt + 1, e, wait)
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch {url} after 4 attempts")


def parse_disclosures(html: str) -> list[Disclosure]:
    """HTML から開示情報のリストをパースする"""
    soup = BeautifulSoup(html, "lxml")
    disclosures: list[Disclosure] = []

    # TDnet のテーブル行を探す
    rows = soup.select("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # 時刻セル
        time_text = cells[0].get_text(strip=True)
        if not re.match(r"\d{1,2}:\d{2}", time_text):
            continue

        # コード・会社名セル
        code_company_text = cells[1].get_text(strip=True)
        code_match = CODE_PATTERN.match(code_company_text)
        if not code_match:
            continue
        code = code_match.group(1)
        company = code_company_text[len(code):].strip()

        # タイトルセル (リンク付き)
        title_cell = cells[2]
        title = title_cell.get_text(strip=True)
        link_tag = title_cell.find("a", href=True)
        pdf_url = ""
        if link_tag:
            href = link_tag["href"]
            if not href.startswith("http"):
                pdf_url = "https://www.release.tdnet.info/inbs/" + href
            else:
                pdf_url = href

        disclosures.append(
            Disclosure(
                time=time_text,
                code=code,
                company=company,
                title=title,
                pdf_url=pdf_url,
            )
        )

    return disclosures


def scrape_all_pages(target_date: date) -> list[Disclosure]:
    """指定日の全ページから開示情報を取得する"""
    all_disclosures: list[Disclosure] = []
    page = 1

    while True:
        html = fetch_page(target_date, page)
        disclosures = parse_disclosures(html)

        if not disclosures:
            break

        all_disclosures.extend(disclosures)
        logger.info("Page %d: %d disclosures found", page, len(disclosures))

        # 次ページがあるか確認
        soup = BeautifulSoup(html, "lxml")
        next_link = soup.find("a", string=re.compile(r"次へ|次のページ|>>"))
        if not next_link:
            # ページ番号リンクで現在のページより大きいものがあるか
            page_links = soup.find_all("a", href=re.compile(rf"I_list_\d+_{target_date.strftime('%Y%m%d')}"))
            has_next = False
            for pl in page_links:
                m = re.search(r"I_list_(\d+)_", pl.get("href", ""))
                if m and int(m.group(1)) > page:
                    has_next = True
                    break
            if not has_next:
                break

        page += 1
        time.sleep(1)  # サーバー負荷軽減

    logger.info("Total: %d disclosures for %s", len(all_disclosures), target_date)
    return all_disclosures
