"""Claude API を使った適時開示スコアリングモジュール

各開示情報を個人投資家目線で 1〜5 でスコアリングし、理由を付与する。
画像のデータ形式:
  時刻 | コード | 会社名 | タイトル | スコア(1-5) | 理由
"""

import json
import logging
import time
from dataclasses import dataclass

import anthropic

from scraper import Disclosure

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたは日本株の個人投資家向けアナリストです。
TDnet（適時開示情報閲覧サービス）に掲載された開示情報を分析し、
個人投資家にとっての投資判断上の重要度をスコアリングしてください。

## スコア基準 (1〜5)

5: 株価に大きなインパクトを与える可能性が極めて高い
   - 例: 大幅な業績上方修正、大型M&A、MBO、株式分割、大幅増配、自社株買い(大規模)
4: 株価に相当のインパクトを与える可能性がある
   - 例: 業績修正(中程度)、新規事業参入、資本業務提携、中程度の増配・自社株買い
3: 投資判断の参考になる注目すべき情報
   - 例: 決算短信(予想通り)、株主優待変更、小規模な業務提携、新製品発表
2: 一般的な開示で特筆すべき点は少ない
   - 例: 定時株主総会招集通知、コーポレートガバナンス報告書、人事異動
1: 投資判断にほぼ影響しない定型的な開示
   - 例: 定款変更、組織変更、規程の改定

## 出力形式
JSON配列で返してください。各要素は以下の形式です:
{"index": 0, "score": 4, "reason": "大幅な業績上方修正により..."}

indexは入力リストの0始まりのインデックスです。
reasonは30文字以内で簡潔に記述してください。
"""


@dataclass
class ScoredDisclosure:
    """スコア付き開示情報"""

    time: str
    code: str
    company: str
    title: str
    score: int
    reason: str
    pdf_url: str


def score_disclosures(
    disclosures: list[Disclosure],
    min_score: int = 3,
    batch_size: int = 30,
) -> list[ScoredDisclosure]:
    """開示情報リストをスコアリングし、min_score 以上のものを返す"""

    client = anthropic.Anthropic()
    scored: list[ScoredDisclosure] = []

    for i in range(0, len(disclosures), batch_size):
        batch = disclosures[i : i + batch_size]
        batch_scored = _score_batch(client, batch, i)
        scored.extend(batch_scored)

        if i + batch_size < len(disclosures):
            time.sleep(1)  # レート制限対策

    # min_score 以上でフィルタリング
    filtered = [s for s in scored if s.score >= min_score]
    filtered.sort(key=lambda x: (-x.score, x.time))

    logger.info(
        "Scored %d disclosures, %d passed filter (score >= %d)",
        len(scored),
        len(filtered),
        min_score,
    )
    return filtered


def _score_batch(
    client: anthropic.Anthropic,
    batch: list[Disclosure],
    offset: int,
) -> list[ScoredDisclosure]:
    """バッチ単位でスコアリング"""

    # 入力テキストを構築
    lines = []
    for idx, d in enumerate(batch):
        lines.append(f"[{idx}] {d.time} | {d.code} {d.company} | {d.title}")
    user_text = "\n".join(lines)

    logger.info("Scoring batch of %d disclosures (offset=%d)", len(batch), offset)

    try:
        with client.messages.stream(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}],
        ) as stream:
            response = stream.get_final_message()

        raw_text = response.content[0].text

        # JSON 部分を抽出 (```json ... ``` で囲まれている場合に対応)
        json_text = raw_text
        if "```" in json_text:
            start = json_text.find("[")
            end = json_text.rfind("]") + 1
            if start >= 0 and end > start:
                json_text = json_text[start:end]

        results = json.loads(json_text)

    except (json.JSONDecodeError, anthropic.APIError) as e:
        logger.error("Failed to score batch at offset %d: %s", offset, e)
        # フォールバック: 全部スコア 1 として返す
        results = [{"index": idx, "score": 1, "reason": "スコアリング失敗"} for idx in range(len(batch))]

    scored = []
    result_map = {r["index"]: r for r in results}

    for idx, d in enumerate(batch):
        r = result_map.get(idx, {"score": 1, "reason": "スコアリング失敗"})
        scored.append(
            ScoredDisclosure(
                time=d.time,
                code=d.code,
                company=d.company,
                title=d.title,
                score=r.get("score", 1),
                reason=r.get("reason", ""),
                pdf_url=d.pdf_url,
            )
        )

    return scored
