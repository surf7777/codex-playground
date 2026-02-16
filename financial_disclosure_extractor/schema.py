"""
Output schema for financial disclosure extraction.
決算開示抽出の出力スキーマ定義。

All fields use original values from source documents.
Numbers retain original units (億円, 千トン, ドル, etc.).
YoY comparisons use % notation.
Missing values are represented as None/null.
Summaries are limited to 100 characters.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Results:
    """業績 (Financial results)."""
    revenue: Optional[str] = None
    revenue_yoy: Optional[str] = None
    operating_profit: Optional[str] = None
    operating_profit_yoy: Optional[str] = None
    net_profit: Optional[str] = None
    net_profit_yoy: Optional[str] = None


@dataclass
class Orders:
    """受注 (Order information)."""
    order_intake: Optional[str] = None
    order_intake_yoy: Optional[str] = None
    order_backlog: Optional[str] = None
    order_backlog_yoy: Optional[str] = None


@dataclass
class CommodityAssumptions:
    """前提商品価格・為替 (Commodity price and FX assumptions)."""
    copper_price: Optional[str] = None
    gold_price: Optional[str] = None
    silver_price: Optional[str] = None
    fx_usdjpy: Optional[str] = None


@dataclass
class SegmentProfit:
    """セグメント利益 (Segment profit entry)."""
    segment_name: str = ""
    profit: Optional[str] = None
    profit_yoy: Optional[str] = None


@dataclass
class Revision:
    """業績修正 (Earnings revision)."""
    full_year_revision: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class FinancialDisclosure:
    """
    Top-level extraction result for a single earnings disclosure.
    決算開示抽出結果の最上位データクラス。
    """
    code: Optional[str] = None
    company: Optional[str] = None
    fiscal_period: Optional[str] = None

    results: Results = field(default_factory=Results)
    orders: Orders = field(default_factory=Orders)
    commodity_assumptions: CommodityAssumptions = field(
        default_factory=CommodityAssumptions
    )

    hedge_description: Optional[str] = None
    inventory_related_note: Optional[str] = None

    revision: Revision = field(default_factory=Revision)

    summary_fact_only: Optional[str] = None
    sensitivity_note: Optional[str] = None
    segment_profit: list[SegmentProfit] = field(default_factory=list)
    capacity_expansion_note: Optional[str] = None
    subsidy_related_note: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to a plain dict suitable for JSON serialization."""
        d = asdict(self)
        return d

    def to_json(self, ensure_ascii: bool = False, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(
            self.to_dict(), ensure_ascii=ensure_ascii, indent=indent
        )

    @classmethod
    def from_dict(cls, data: dict) -> "FinancialDisclosure":
        """Construct from a plain dict (e.g. parsed JSON)."""
        results = Results(**data.get("results", {}))
        orders = Orders(**data.get("orders", {}))
        commodity = CommodityAssumptions(**data.get("commodity_assumptions", {}))
        revision = Revision(**data.get("revision", {}))
        segments = [
            SegmentProfit(**s) for s in data.get("segment_profit", [])
        ]
        return cls(
            code=data.get("code"),
            company=data.get("company"),
            fiscal_period=data.get("fiscal_period"),
            results=results,
            orders=orders,
            commodity_assumptions=commodity,
            hedge_description=data.get("hedge_description"),
            inventory_related_note=data.get("inventory_related_note"),
            revision=revision,
            summary_fact_only=data.get("summary_fact_only"),
            sensitivity_note=data.get("sensitivity_note"),
            segment_profit=segments,
            capacity_expansion_note=data.get("capacity_expansion_note"),
            subsidy_related_note=data.get("subsidy_related_note"),
        )
