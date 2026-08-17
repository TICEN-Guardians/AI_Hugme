"""
OcrRegisterResponse / RegisterCheckResponse를 Spring 에서 생성된
registry_results / registry_owners / registry_rights / landlord_watchlist_checks
테이블에 저장.
"""
from datetime import datetime, timezone

from app.ocr.db import get_connection
from app.ocr.schemas import OcrRegisterResponse, RegisterCheckResponse

_SECTION_MAP = {"갑구": "GAP", "을구": "EUL"}


def _now():
    return datetime.now(timezone.utc)


def save_registry_result(
    analysis_id: str, owner_info: OcrRegisterResponse
) -> tuple[int, dict[str, int]]:
    """
    registry_results 1행 + registry_owners N행 + registry_rights N행을 저장하고
    registry_result_id를 반환
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            now = _now()
            s = owner_info.summary

            cur.execute(
                """
                INSERT INTO registry_results (
                    analysis_id, parse_status, parse_confidence, raw_address, issue_date,
                    source_type, raw_text, has_cancellation_mention,
                    gap_section_status, eul_section_status,
                    seizure, provisional_seizure, provisional_disposition,
                    auction_commenced, trust_registration,
                    has_active_jeonse_right, has_active_leasehold_registration,
                    active_mortgage_count, total_active_max_claim_amount,
                    parsed_at, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s
                )
                RETURNING registry_result_id
                """,
                (
                    analysis_id,
                    owner_info.parse_status,
                    owner_info.parse_confidence,
                    owner_info.raw_address,
                    owner_info.issue_date,
                    owner_info.source_type.upper(),
                    owner_info.raw_text,
                    owner_info.has_cancellation_mention,
                    s.gap_section_status,
                    s.eul_section_status,
                    s.seizure,
                    s.provisional_seizure,
                    s.provisional_disposition,
                    s.auction_commenced,
                    s.trust_registration,
                    s.has_active_jeonse_right,
                    s.has_active_leasehold_registration,
                    s.active_mortgage_count,
                    s.total_active_max_claim_amount,
                    now,
                    now,
                ),
            )
            registry_result_id = cur.fetchone()[0]

            owner_ids: dict[str, int] = {}
            for owner in owner_info.current_owners:
                cur.execute(
                    """
                    INSERT INTO registry_owners (
                        registry_result_id, name, jumin_front, address, share, status, age,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING registry_owner_id
                    """,
                    (
                        registry_result_id,
                        owner.name,
                        owner.jumin_front,
                        owner.address,
                        owner.share,
                        owner.status,
                        owner.age,
                        now,
                    ),
                )
                owner_ids[owner.name] = cur.fetchone()[0]

            for right in owner_info.rights:
                cur.execute(
                    """
                    INSERT INTO registry_rights (
                        registry_result_id, section, right_type, rank_no, receipt_no,
                        registered_at, holder, debtor, amount, status, raw_text, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        registry_result_id,
                        _SECTION_MAP.get(right.section, right.section),
                        right.kind,
                        right.rank_no,
                        right.receipt_no,
                        right.registered_at,
                        right.holder,
                        right.debtor,
                        right.amount,
                        right.status,
                        right.raw_text,
                        now,
                    ),
                )

        conn.commit()
        return registry_result_id, owner_ids
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_watchlist_checks(
    analysis_id: str,
    registry_result_id: int,
    owner_ids: dict[str, int],
    check_result: RegisterCheckResponse,
) -> None:
    """소유자별 악성임대인 대조 결과를 landlord_watchlist_checks에 저장."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for r in check_result.results:
                registry_owner_id = owner_ids.get(r.owner.name) if r.owner else None
                cur.execute(
                    """
                    INSERT INTO landlord_watchlist_checks (
                        analysis_id, registry_result_id, registry_owner_id,
                        check_status, match_status, matched, match_type,
                        source, checked_at, details_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        analysis_id,
                        registry_result_id,
                        registry_owner_id,
                        r.check_status,
                        r.match_status,
                        r.matched,
                        r.match_type,
                        r.source,
                        r.checked_at or _now(),
                        _candidates_to_json(r.match_candidates),
                        _now(),
                    ),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _candidates_to_json(candidates) -> str | None:
    import json
    if not candidates:
        return None
    return json.dumps([c.model_dump() for c in candidates], ensure_ascii=False, default=str)
