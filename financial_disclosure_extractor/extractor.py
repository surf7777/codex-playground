"""
Core extraction engine for Japanese financial disclosures (決算短信).

Design principles:
- Extract facts only; no evaluation, speculation, or commentary.
- Preserve original numbers, units (億円, 百万円, 千トン, ドル, etc.).
- YoY comparisons always in % notation.
- Missing data → None.
- Summary capped at 100 characters.
"""

from __future__ import annotations

import re
from typing import Optional

from .schema import (
    CommodityAssumptions,
    FinancialDisclosure,
    Orders,
    Results,
    Revision,
    SegmentProfit,
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _first_match(pattern: str, text: str, group: int = 1) -> Optional[str]:
    """Return the first regex match group or None."""
    m = re.search(pattern, text)
    if m:
        return m.group(group).strip()
    return None


def _extract_yoy(text: str, label_patterns: list[str]) -> Optional[str]:
    """
    Look for year-over-year percentage near a label.
    Patterns like: 前年同期比 12.3%増, 前年比△5.2%, (前年同期比+8.0%)
    """
    for label in label_patterns:
        pattern = (
            label
            + r"[^\d△▲\-]*"
            + r"(前年同期比|前年比)?\s*"
            + r"([△▲\-\+]?\s*[\d,]+\.?\d*\s*%)"
        )
        m = re.search(pattern, text)
        if m:
            raw = m.group(2).strip()
            # Normalize △/▲ → -
            raw = re.sub(r"[△▲]", "-", raw)
            return raw

    # Fallback: look for (前年同期比 XX.X%増/減) near the label
    for label in label_patterns:
        block_pat = label + r".{0,80}?前年同期比\s*([△▲\-\+]?\s*[\d,]+\.?\d*\s*%)"
        m = re.search(block_pat, text, re.DOTALL)
        if m:
            raw = m.group(1).strip()
            raw = re.sub(r"[△▲]", "-", raw)
            return raw

    return None


def _extract_amount(text: str, label_patterns: list[str]) -> Optional[str]:
    """
    Extract a monetary amount following a label.
    Preserves original unit (億円, 百万円, 千円, etc.).
    """
    for label in label_patterns:
        pattern = label + r"\s*[:：]?\s*([\d,]+\.?\d*\s*(?:億円|百万円|千円|円|百万ドル|千ドル|ドル))"
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
    return None


def _clamp_summary(text: Optional[str], max_len: int = 100) -> Optional[str]:
    """Truncate summary to max_len characters."""
    if text is None:
        return None
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


# ---------------------------------------------------------------------------
# Section extractors
# ---------------------------------------------------------------------------

def _extract_company_info(text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract securities code, company name, and fiscal period."""
    # Securities code: 4-digit number often labelled コード or near company name
    code = _first_match(r"(?:コード|証券コード)[：:\s]*(\d{4})", text)
    if code is None:
        # Try standalone 4-digit code pattern common in tanshin headers
        code = _first_match(r"(?:^|\s)(\d{4})(?:\s|　)", text)

    # Company name: prefer explicit label first (most reliable)
    company = _first_match(r"上場会社名\s*[:：]?\s*(.+?)(?:\s{2,}|\n)", text)
    if company is None:
        # Fallback: look for 株式会社 pattern
        company = _first_match(
            r"((?:株式会社\s*)?[^\s\d（(\n]{2,30}(?:株式会社|㈱))\s",
            text,
        )
    if company is None:
        # Fallback: company name before 決算短信
        company = _first_match(
            r"([^\s\d（(\n]{2,30})\s*(?:[\(（]?\d{4}[\)）]?)\s*決算",
            text,
        )

    # Fiscal period
    fiscal_period = _first_match(
        r"(\d{4}年\d{1,2}月期\s*(?:第[一二三四1-4]四半期|通期|半期|中間)?)\s*(?:決算|連結|個別)?",
        text,
    )
    if fiscal_period is None:
        fiscal_period = _first_match(
            r"((?:20\d{2}|令和\d+)年[度]?\d{0,2}月?期?\s*(?:第[一二三四1-4]四半期|通期|半期|中間期)?)",
            text,
        )

    return code, company, fiscal_period


def _extract_results(text: str) -> Results:
    """Extract revenue, operating profit, net profit and their YoY."""
    revenue_labels = [r"売上高", r"売上収益", r"営業収益", r"Revenue"]
    op_labels = [r"営業利益", r"Operating\s*(?:profit|income)"]
    np_labels = [r"(?:親会社株主に帰属する)?(?:当期)?純利益", r"Net\s*(?:profit|income)"]

    revenue = _extract_amount(text, revenue_labels)
    revenue_yoy = _extract_yoy(text, revenue_labels)
    operating_profit = _extract_amount(text, op_labels)
    operating_profit_yoy = _extract_yoy(text, op_labels)
    net_profit = _extract_amount(text, np_labels)
    net_profit_yoy = _extract_yoy(text, np_labels)

    # --- Fallback: table-style extraction for tanshin formats ---
    # Many 決算短信 use table rows like:
    #   売上高  |  1,234,567  |  5.6
    # where columns are separated by whitespace/tabs.
    if revenue is None:
        for label in revenue_labels:
            m = re.search(
                label + r"\s+([\d,]+)\s+([\d,]+\.?\d*)", text
            )
            if m:
                revenue = m.group(1).strip()
                break

    if operating_profit is None:
        for label in op_labels:
            m = re.search(
                label + r"\s+([\d,]+)\s+([\d,]+\.?\d*)", text
            )
            if m:
                operating_profit = m.group(1).strip()
                break

    if net_profit is None:
        for label in np_labels:
            m = re.search(
                label + r"\s+([\d,]+)\s+([\d,]+\.?\d*)", text
            )
            if m:
                net_profit = m.group(1).strip()
                break

    return Results(
        revenue=revenue,
        revenue_yoy=revenue_yoy,
        operating_profit=operating_profit,
        operating_profit_yoy=operating_profit_yoy,
        net_profit=net_profit,
        net_profit_yoy=net_profit_yoy,
    )


def _extract_orders(text: str) -> Orders:
    """Extract order intake and order backlog."""
    intake_labels = [r"受注高", r"受注額", r"Order\s*intake"]
    backlog_labels = [r"受注残高", r"受注残", r"Order\s*backlog"]

    return Orders(
        order_intake=_extract_amount(text, intake_labels),
        order_intake_yoy=_extract_yoy(text, intake_labels),
        order_backlog=_extract_amount(text, backlog_labels),
        order_backlog_yoy=_extract_yoy(text, backlog_labels),
    )


def _extract_commodity_assumptions(text: str) -> CommodityAssumptions:
    """Extract commodity price / FX assumptions."""
    copper = _first_match(
        r"(?:銅価格?|copper)[：:\s]*([\d,]+\.?\d*\s*(?:ドル|USD|セント|円|¢/lb)?(?:/(?:トン|lb|ポンド))?)",
        text, 1
    )
    gold = _first_match(
        r"(?:金価格?|gold)[：:\s]*([\d,]+\.?\d*\s*(?:ドル|USD|円)?(?:/(?:トロイオンス|oz))?)",
        text, 1
    )
    silver = _first_match(
        r"(?:銀価格?|silver)[：:\s]*([\d,]+\.?\d*\s*(?:ドル|USD|セント|円)?(?:/(?:トロイオンス|oz))?)",
        text, 1
    )
    fx = _first_match(
        r"(?:為替|(?:USD\s*/?\s*JPY)|(?:ドル\s*[/／]\s*円)|(?:米ドル))[：:\s]*([\d,]+\.?\d*\s*円(?:/(?:ドル|USD))?)",
        text, 1
    )
    if fx is None:
        fx = _first_match(r"(?:1ドル|1USD)\s*[=＝]\s*([\d,]+\.?\d*\s*円)", text, 1)

    return CommodityAssumptions(
        copper_price=copper,
        gold_price=gold,
        silver_price=silver,
        fx_usdjpy=fx,
    )


def _extract_hedge_description(text: str) -> Optional[str]:
    """Extract hedging-related description."""
    m = re.search(
        r"(ヘッジ|hedg(?:e|ing))[^\n]{0,200}",
        text, re.IGNORECASE,
    )
    if m:
        return _clamp_summary(m.group(0), 100)
    return None


def _extract_inventory_note(text: str) -> Optional[str]:
    """Extract inventory-related notes."""
    m = re.search(
        r"(棚卸資産|在庫|inventory)[^\n]{0,200}",
        text, re.IGNORECASE,
    )
    if m:
        return _clamp_summary(m.group(0), 100)
    return None


def _extract_revision(text: str) -> Revision:
    """Extract earnings revision information."""
    rev_text = None
    reason = None

    m = re.search(
        r"(業績予想の修正|通期[業績]*予想.*?修正|修正後|修正前)[^\n]*",
        text,
    )
    if m:
        rev_text = _clamp_summary(m.group(0), 100)

    m = re.search(
        r"(?:修正[のの]?理由|修正理由)[：:\s]*(.+?)(?:\n\n|\n[^\s]|\Z)",
        text, re.DOTALL,
    )
    if m:
        reason = _clamp_summary(m.group(1), 100)

    has_revision = rev_text is not None or reason is not None
    if not has_revision:
        # Check for "修正なし" / no revision
        if re.search(r"修正.{0,5}(?:ありません|なし|行っておりません)", text):
            rev_text = "修正なし"

    return Revision(full_year_revision=rev_text, reason=reason)


def _extract_segment_profit(text: str) -> list[SegmentProfit]:
    """Extract segment-level profit entries."""
    segments: list[SegmentProfit] = []

    # Pattern: セグメント名  利益 XX億円  前年同期比 YY.Y%
    pattern = (
        r"(?:セグメント|事業)[\s\S]{0,20}?"
        r"([^\n\d]{2,20}?)\s+"
        r"(?:セグメント利益|営業利益|利益)\s*[:：]?\s*"
        r"([\d,]+\.?\d*\s*(?:億円|百万円|千円|円))"
    )
    for m in re.finditer(pattern, text):
        name = m.group(1).strip()
        profit = m.group(2).strip()
        segments.append(SegmentProfit(segment_name=name, profit=profit))

    # Alternative: tabular format
    # セグメント名 | XX,XXX | YY.Y%
    if not segments:
        block = re.search(
            r"セグメント(?:別|情報|利益).*?\n((?:.*\n){1,20})",
            text,
        )
        if block:
            for line in block.group(1).split("\n"):
                cols = re.split(r"\s{2,}|\t+|\|", line.strip())
                if len(cols) >= 2:
                    name_candidate = cols[0].strip()
                    val_candidate = cols[1].strip()
                    if name_candidate and re.search(r"\d", val_candidate):
                        seg = SegmentProfit(
                            segment_name=name_candidate,
                            profit=val_candidate,
                        )
                        segments.append(seg)

    return segments


def _extract_sensitivity_note(text: str) -> Optional[str]:
    """Extract sensitivity analysis note."""
    m = re.search(
        r"(感応度|sensitivity)[^\n]{0,200}",
        text, re.IGNORECASE,
    )
    if m:
        return _clamp_summary(m.group(0), 100)
    return None


def _extract_capacity_expansion_note(text: str) -> Optional[str]:
    """Extract capacity expansion / capex note."""
    m = re.search(
        r"(設備投資|生産能力|増産|capacity|capex)[^\n]{0,200}",
        text, re.IGNORECASE,
    )
    if m:
        return _clamp_summary(m.group(0), 100)
    return None


def _extract_subsidy_note(text: str) -> Optional[str]:
    """Extract subsidy-related note."""
    m = re.search(
        r"(補助金|助成金|subsid(?:y|ies))[^\n]{0,200}",
        text, re.IGNORECASE,
    )
    if m:
        return _clamp_summary(m.group(0), 100)
    return None


def _build_summary(text: str) -> Optional[str]:
    """
    Build a fact-only summary (max 100 chars) from the earnings overview.
    Looks for the 経営成績 or 業績の概要 section.
    """
    m = re.search(
        r"(?:経営成績|業績)[のに]概要[^\n]*\n(.+?)(?:\n\n|\n[（(]?\d|\Z)",
        text, re.DOTALL,
    )
    if m:
        raw = m.group(1).strip().replace("\n", "")
        return _clamp_summary(raw, 100)

    # Fallback: first meaningful paragraph
    for line in text.split("\n"):
        line = line.strip()
        if len(line) > 30 and not re.match(r"^[\d\s\-/|]+$", line):
            return _clamp_summary(line, 100)

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract(text: str) -> FinancialDisclosure:
    """
    Extract structured financial disclosure data from raw text.

    Parameters
    ----------
    text : str
        Full text of 決算短信 / supplementary materials.

    Returns
    -------
    FinancialDisclosure
        Structured extraction result.
    """
    code, company, fiscal_period = _extract_company_info(text)

    return FinancialDisclosure(
        code=code,
        company=company,
        fiscal_period=fiscal_period,
        results=_extract_results(text),
        orders=_extract_orders(text),
        commodity_assumptions=_extract_commodity_assumptions(text),
        hedge_description=_extract_hedge_description(text),
        inventory_related_note=_extract_inventory_note(text),
        revision=_extract_revision(text),
        summary_fact_only=_build_summary(text),
        sensitivity_note=_extract_sensitivity_note(text),
        segment_profit=_extract_segment_profit(text),
        capacity_expansion_note=_extract_capacity_expansion_note(text),
        subsidy_related_note=_extract_subsidy_note(text),
    )
