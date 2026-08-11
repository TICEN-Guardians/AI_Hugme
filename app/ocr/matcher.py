"""
등기부등본에서 뽑은 소유자(임대인)를 bad_landlord 테이블과 대조.

매칭 기준:
- 이름 완전일치 + 시군구 일치        -> MATCH_HIGH   (신뢰도 높음)
- 이름만 일치 (시군구 다르거나 없음)  -> MATCH_NAME_ONLY (사람이 재확인 필요)
- 이름조차 안 걸림                  -> NO_MATCH
"""
from dataclasses import dataclass, field

from app.ocr.db import get_connection


@dataclass
class MatchResult:
    status: str  # "MATCH_HIGH" | "MATCH_NAME_ONLY" | "NO_MATCH"
    candidates: list[dict] = field(default_factory=list)


def decide_match(rows: list[dict], sigungu: str | None) -> str:
    """
    DB에서 이름으로 조회한 결과와, 등기부등본에서 뽑은 시군구를 비교해 매칭 등급을 결정하는 함수
    """
    if not rows:
        return "NO_MATCH"

    if sigungu and any(r.get("address_sigungu") == sigungu for r in rows):
        return "MATCH_HIGH"

    return "MATCH_NAME_ONLY"


def _fetch_by_name(name: str) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, age, address, address_sigungu,
                       return_debt_amount, default_days,
                       enforcement_count, posted_date
                FROM bad_landlord
                WHERE name = %s
                """,
                (name,),
            )
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in cur.fetchall():
                record = dict(zip(columns, row))
                if record.get("posted_date") is not None:
                    record["posted_date"] = record["posted_date"].isoformat()
                results.append(record)
            return results
    finally:
        conn.close()


def find_bad_landlord_matches(name: str | None, sigungu: str | None) -> MatchResult:
    if not name:
        return MatchResult(status="NO_MATCH", candidates=[])

    rows = _fetch_by_name(name)
    status = decide_match(rows, sigungu)
    return MatchResult(status=status, candidates=rows)
