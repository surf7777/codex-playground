"""
edinetdb.jp からデータを収集して CSV に保存するスクリプト

取得データ:
  1. 企業一覧 (companies)
  2. 各企業の財務データ (financials)
  3. ランキングデータ (ROE等)

使い方:
  pip install -r requirements.txt
  python collect_edinetdb.py
"""

import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://edinetdb.jp/v1"
API_KEY = os.getenv("EDINETDB_API_KEY")
OUTPUT_DIR = Path("output")
PER_PAGE = 100
REQUEST_INTERVAL = 0.5  # API負荷軽減のため0.5秒間隔


def get_headers():
    return {
        "X-API-Key": API_KEY,
        "Accept": "application/json",
    }


def api_get(endpoint, params=None, max_retries=3):
    """APIリクエストを実行する（リトライ付き）"""
    url = f"{BASE_URL}{endpoint}"
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=get_headers(), params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  レート制限。{wait}秒待機...")
                time.sleep(wait)
                continue
            raise
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  リクエスト失敗 ({e})。{wait}秒後にリトライ...")
                time.sleep(wait)
                continue
            raise
    return None


# ─── 1. 企業一覧の取得 ─────────────────────────────────────────

def fetch_all_companies():
    """全企業一覧をページネーションで取得する"""
    print("=== 企業一覧を取得中 ===")
    all_companies = []
    page = 1

    while True:
        print(f"  ページ {page} を取得中...")
        data = api_get("/companies", params={"per_page": PER_PAGE, "page": page})
        if data is None:
            break

        # レスポンスがリスト形式の場合
        if isinstance(data, list):
            if not data:
                break
            all_companies.extend(data)
            if len(data) < PER_PAGE:
                break
        # レスポンスがオブジェクト形式 (data/results キー) の場合
        elif isinstance(data, dict):
            items = data.get("data") or data.get("results") or data.get("companies", [])
            if not items:
                break
            all_companies.extend(items)
            # ページネーション終了判定
            total_pages = data.get("total_pages") or data.get("last_page")
            if total_pages and page >= total_pages:
                break
            if len(items) < PER_PAGE:
                break
        else:
            break

        page += 1
        time.sleep(REQUEST_INTERVAL)

    print(f"  合計 {len(all_companies)} 社を取得しました")
    return all_companies


def save_companies_csv(companies):
    """企業一覧をCSVに保存する"""
    if not companies:
        print("  企業データがありません。スキップします。")
        return

    filepath = OUTPUT_DIR / "companies.csv"
    # 全てのキーを集めてヘッダーにする
    all_keys = []
    for c in companies:
        for k in c.keys():
            if k not in all_keys:
                all_keys.append(k)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(companies)

    print(f"  -> {filepath} に保存しました ({len(companies)} 件)")


# ─── 2. 財務データの取得 ────────────────────────────────────────

def fetch_financials(edinet_code):
    """指定企業の財務データを取得する"""
    data = api_get(f"/companies/{edinet_code}/financials")
    return data


def fetch_all_financials(companies):
    """全企業の財務データを取得する"""
    print("\n=== 財務データを取得中 ===")
    all_financials = []
    total = len(companies)

    for i, company in enumerate(companies, 1):
        # EDINET コードを取得（キー名はAPIレスポンスによる）
        edinet_code = (
            company.get("edinet_code")
            or company.get("edinetCode")
            or company.get("code")
            or company.get("id")
        )
        company_name = (
            company.get("name")
            or company.get("company_name")
            or company.get("filer_name")
            or "不明"
        )

        if not edinet_code:
            continue

        print(f"  [{i}/{total}] {company_name} ({edinet_code})")
        try:
            data = fetch_financials(edinet_code)
            if data is None:
                continue

            # レスポンスがリスト形式の場合
            if isinstance(data, list):
                for item in data:
                    item["edinet_code"] = edinet_code
                    item["company_name"] = company_name
                all_financials.extend(data)
            # レスポンスがオブジェクト形式の場合
            elif isinstance(data, dict):
                items = data.get("data") or data.get("results") or data.get("financials")
                if isinstance(items, list):
                    for item in items:
                        item["edinet_code"] = edinet_code
                        item["company_name"] = company_name
                    all_financials.extend(items)
                else:
                    # 単一の財務データ
                    data["edinet_code"] = edinet_code
                    data["company_name"] = company_name
                    all_financials.append(data)

        except Exception as e:
            print(f"    エラー: {e}")

        time.sleep(REQUEST_INTERVAL)

    print(f"  合計 {len(all_financials)} 件の財務データを取得しました")
    return all_financials


def save_financials_csv(financials):
    """財務データをCSVに保存する"""
    if not financials:
        print("  財務データがありません。スキップします。")
        return

    filepath = OUTPUT_DIR / "financials.csv"
    all_keys = []
    for item in financials:
        for k in item.keys():
            if k not in all_keys:
                all_keys.append(k)

    # edinet_code と company_name を先頭に持ってくる
    priority = ["edinet_code", "company_name"]
    ordered_keys = [k for k in priority if k in all_keys]
    ordered_keys += [k for k in all_keys if k not in priority]

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ordered_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(financials)

    print(f"  -> {filepath} に保存しました ({len(financials)} 件)")


# ─── 3. ランキングデータの取得 ──────────────────────────────────

RANKING_TYPES = ["roe", "roa", "revenue", "profit", "market_cap"]


def fetch_ranking(ranking_type, limit=100):
    """ランキングデータを取得する"""
    data = api_get(f"/rankings/{ranking_type}", params={"limit": limit})
    return data


def fetch_all_rankings():
    """全ランキングデータを取得する"""
    print("\n=== ランキングデータを取得中 ===")
    all_rankings = {}

    for rtype in RANKING_TYPES:
        print(f"  {rtype} ランキングを取得中...")
        try:
            data = fetch_ranking(rtype)
            if data is None:
                continue

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("data") or data.get("results") or data.get("rankings", [])
            else:
                items = []

            if items:
                # ランキング種別を各レコードに追加
                for item in items:
                    item["ranking_type"] = rtype
                all_rankings[rtype] = items
                print(f"    {len(items)} 件取得")
            else:
                print(f"    データなし")

        except Exception as e:
            print(f"    エラー: {e}")

        time.sleep(REQUEST_INTERVAL)

    return all_rankings


def save_rankings_csv(all_rankings):
    """ランキングデータをCSVに保存する"""
    if not all_rankings:
        print("  ランキングデータがありません。スキップします。")
        return

    # ランキング種別ごとに個別CSV
    for rtype, items in all_rankings.items():
        filepath = OUTPUT_DIR / f"ranking_{rtype}.csv"
        all_keys = []
        for item in items:
            for k in item.keys():
                if k not in all_keys:
                    all_keys.append(k)

        # ranking_type を先頭に
        if "ranking_type" in all_keys:
            all_keys.remove("ranking_type")
            all_keys.insert(0, "ranking_type")

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(items)

        print(f"  -> {filepath} に保存しました ({len(items)} 件)")

    # 全ランキングを1つにまとめたCSVも作成
    all_items = []
    for items in all_rankings.values():
        all_items.extend(items)

    if all_items:
        filepath = OUTPUT_DIR / "rankings_all.csv"
        all_keys = []
        for item in all_items:
            for k in item.keys():
                if k not in all_keys:
                    all_keys.append(k)

        if "ranking_type" in all_keys:
            all_keys.remove("ranking_type")
            all_keys.insert(0, "ranking_type")

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_items)

        print(f"  -> {filepath} に保存しました (全{len(all_items)} 件)")


# ─── メイン処理 ─────────────────────────────────────────────────

def main():
    if not API_KEY:
        print("エラー: EDINETDB_API_KEY が設定されていません。")
        print(".env ファイルに EDINETDB_API_KEY=your_api_key を記載してください。")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)

    start_time = datetime.now()
    print(f"データ収集開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print()

    # 1. 企業一覧
    companies = fetch_all_companies()
    save_companies_csv(companies)

    # 2. 財務データ
    financials = fetch_all_financials(companies)
    save_financials_csv(financials)

    # 3. ランキングデータ
    all_rankings = fetch_all_rankings()
    save_rankings_csv(all_rankings)

    end_time = datetime.now()
    elapsed = end_time - start_time
    print(f"\n=== 完了 ===")
    print(f"所要時間: {elapsed}")
    print(f"出力先: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
