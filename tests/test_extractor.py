"""Tests for the financial disclosure extractor."""

from __future__ import annotations

import json

from financial_disclosure_extractor.extractor import extract
from financial_disclosure_extractor.schema import FinancialDisclosure


# ---------------------------------------------------------------------------
# Sample 決算短信-style text (synthetic, representative)
# ---------------------------------------------------------------------------

SAMPLE_TANSHIN = """\
2025年3月期 第3四半期決算短信〔日本基準〕（連結）
                                                    2025年2月7日
上場会社名：  住友金属鉱山株式会社
コード：5713　　上場取引所：東証プライム

１．2025年3月期第3四半期の連結業績（2024年4月1日～2024年12月31日）
（１）連結経営成績（累計）
                       売上高            営業利益          当期純利益
                     (百万円) (%)     (百万円) (%)      (百万円) (%)
2025年3月期第3四半期  1,023,456  12.3   85,432  前年同期比 25.1%   52,789  前年同期比 30.4%
2024年3月期第3四半期    911,234   8.1   68,289            40,486

売上高は前年同期比 12.3%増の1,023,456百万円となりました。

（２）受注・受注残高
受注高：450,000百万円（前年同期比 8.5%増）
受注残高：680,000百万円（前年同期比 3.2%増）

２．前提条件
銅価格：9,200ドル/トン
金価格：2,050ドル/トロイオンス
銀価格：25.5ドル/トロイオンス
為替：1ドル＝148円

３．ヘッジ方針
ヘッジ取引は銅地金の販売価格変動リスクを回避するため先物取引を実施。

４．棚卸資産
棚卸資産は前期末比10,500百万円増加し、主に銅地金在庫の増加による。

５．セグメント情報
セグメント別の状況：
資源セグメント  営業利益：45,000百万円
製錬セグメント  営業利益：28,000百万円
材料セグメント  営業利益：12,432百万円

６．業績予想の修正
業績予想の修正：通期売上高を1,380,000百万円に上方修正。
修正の理由：銅価格の上昇および円安の進行により、売上高・利益ともに従来予想を上回る見通し。

７．感応度分析
感応度：銅価格が100ドル/トン変動した場合、営業利益に約15億円の影響。

８．設備投資
設備投資は新規鉱山開発に伴い前年同期比20%増の35,000百万円を計画。

９．補助金
補助金として環境対策関連で500百万円を受領。
"""


def test_extract_basic_fields():
    result = extract(SAMPLE_TANSHIN)
    assert isinstance(result, FinancialDisclosure)
    assert result.code == "5713"
    assert result.company is not None
    assert "住友金属鉱山" in (result.company or "")
    assert result.fiscal_period is not None
    assert "2025年3月期" in (result.fiscal_period or "")


def test_extract_results():
    result = extract(SAMPLE_TANSHIN)
    r = result.results
    # Revenue YoY should be captured
    assert r.revenue_yoy is not None
    assert "12.3%" in r.revenue_yoy


def test_extract_orders():
    result = extract(SAMPLE_TANSHIN)
    o = result.orders
    assert o.order_intake is not None
    assert "450,000" in (o.order_intake or "")
    assert o.order_intake_yoy is not None
    assert "8.5%" in o.order_intake_yoy


def test_extract_commodity_assumptions():
    result = extract(SAMPLE_TANSHIN)
    c = result.commodity_assumptions
    assert c.copper_price is not None
    assert "9,200" in (c.copper_price or "")
    assert c.gold_price is not None
    assert "2,050" in (c.gold_price or "")
    assert c.fx_usdjpy is not None
    assert "148" in (c.fx_usdjpy or "")


def test_extract_hedge_description():
    result = extract(SAMPLE_TANSHIN)
    assert result.hedge_description is not None
    assert "ヘッジ" in result.hedge_description


def test_extract_inventory_note():
    result = extract(SAMPLE_TANSHIN)
    assert result.inventory_related_note is not None
    assert "棚卸資産" in result.inventory_related_note


def test_extract_revision():
    result = extract(SAMPLE_TANSHIN)
    rev = result.revision
    assert rev.full_year_revision is not None
    assert "修正" in (rev.full_year_revision or "")
    assert rev.reason is not None
    assert "銅価格" in (rev.reason or "")


def test_extract_sensitivity():
    result = extract(SAMPLE_TANSHIN)
    assert result.sensitivity_note is not None
    assert "感応度" in result.sensitivity_note


def test_extract_capacity_expansion():
    result = extract(SAMPLE_TANSHIN)
    assert result.capacity_expansion_note is not None
    assert "設備投資" in result.capacity_expansion_note


def test_extract_subsidy():
    result = extract(SAMPLE_TANSHIN)
    assert result.subsidy_related_note is not None
    assert "補助金" in result.subsidy_related_note


def test_summary_max_100_chars():
    result = extract(SAMPLE_TANSHIN)
    if result.summary_fact_only is not None:
        assert len(result.summary_fact_only) <= 100


def test_to_json_roundtrip():
    result = extract(SAMPLE_TANSHIN)
    json_str = result.to_json()
    parsed = json.loads(json_str)
    assert parsed["code"] == result.code
    assert parsed["results"]["revenue_yoy"] == result.results.revenue_yoy

    # Roundtrip via from_dict
    restored = FinancialDisclosure.from_dict(parsed)
    assert restored.code == result.code
    assert restored.results.revenue_yoy == result.results.revenue_yoy


def test_empty_input():
    """Extraction on empty text should return all-None fields without errors."""
    result = extract("")
    assert result.code is None
    assert result.results.revenue is None
    assert result.orders.order_intake is None
    assert result.segment_profit == []


def test_segment_profit():
    """Verify segment profits are extracted."""
    result = extract(SAMPLE_TANSHIN)
    # We should have at least one segment
    assert len(result.segment_profit) > 0
    names = [s.segment_name for s in result.segment_profit]
    # Check at least one known segment name appears
    found = any("資源" in n or "製錬" in n or "材料" in n for n in names)
    assert found, f"Expected known segment names, got: {names}"
