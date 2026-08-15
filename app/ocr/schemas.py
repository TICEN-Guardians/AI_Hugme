from typing import List
from pydantic import BaseModel, Field


class OwnershipEntry(BaseModel):
    """등기부등본 갑구에 기록된 소유권 이력."""

    name: str = Field(..., description="소유자 성명", examples=["김민수"])
    jumin_front: str = Field(
        ..., description="주민등록번호 앞자리(뒷자리는 마스킹됨)", examples=["980101-*******"]
    )
    address: str = Field(..., description="등기부등본에 기록된 소유자 주소")

class CurrentOwner(BaseModel):
    """현재 소유자 1명, 공유자의 경우 List[CurrentOwner]"""
 
    name: str = Field(..., description="소유자 성명")
    jumin_front: str = Field(..., description="주민등록번호 앞자리")
    address: str = Field(..., description="주소 원문")
    share: str | None = Field(None, description="지분 (예: '1/1', '1/2')")
    status: str = Field("CURRENT", description="CURRENT (현재 유효 소유자)")
    age: int | None = Field(None, description="주민번호 앞자리에서 역산한 나이")

class RightEntry(BaseModel):
    """갑구/을구의 등기 항목 1건 원본"""

    section: str = Field(..., description="갑구 | 을구")
    rank_no: str = Field(..., description="순위번호 (부기등기는 '1-1' 형태)")
    kind: str = Field(..., description="rightType: MORTGAGE/SEIZURE/PROVISIONAL_SEIZURE/"
                                       "PROVISIONAL_DISPOSITION/AUCTION/TRUST/JEONSE_RIGHT/"
                                       "LEASEHOLD_REGISTRATION/OWNERSHIP/MORTGAGE_AMEND/"
                                       "CANCELLATION/OTHER")
    status: str = Field(..., description="ACTIVE | CANCELLED (말소 항목의 순위번호 참조로 판정)")
    receipt_no: str | None = Field(None, description="접수번호")
    registered_at: str | None = Field(None, description="접수일 (YYYY-MM-DD)")
    holder: str | None = Field(None, description="권리자 (근저당권자/전세권자/임차권자/채권자 등)")
    debtor: str | None = Field(None, description="채무자")
    amount: int | None = Field(None, description="금액 (채권최고액/전세금/임차보증금/청구금액)")
    raw_text: str = Field(..., description="항목 원문 (공백 정규화)")

class Mortgage(BaseModel):
    rank_no: str = Field(..., description="순위번호")
    receipt_no: str | None = Field(None, description="접수번호")
    registered_at: str | None = Field(None, description="설정일 (YYYY-MM-DD)")
    creditor: str | None = Field(None, description="근저당권자")
    debtor: str | None = Field(None, description="채무자")
    max_claim_amount: int | None = Field(
        None, description="채권최고액(원). 근저당권변경 부기가 있으면 변경 후 금액."
    )
    status: str = Field(..., description="ACTIVE | CANCELLED")

class DepositRight(BaseModel):
    """전세권 또는 임차권등기 1건"""

    rank_no: str = Field(..., description="순위번호")
    receipt_no: str | None = Field(None, description="접수번호")
    registered_at: str | None = Field(None, description="설정일 (YYYY-MM-DD)")
    holder: str | None = Field(None, description="전세권자 / 임차권자")
    deposit_amount: int | None = Field(None, description="전세금/임차보증금(원)")
    status: str = Field(..., description="ACTIVE | CANCELLED")

class BadLandlordCandidate(BaseModel):
    """HUG 상습채무불이행자 명단에서 조회된 후보 1건"""

    name: str = Field(..., description="성명")
    age: int | None = Field(None, description="나이(법인 임대인은 None)")
    address: str = Field(..., description="주소 원문")
    address_sigungu: str | None = Field(None, description="시/군/구")
    return_debt_amount: int | None = Field(None, description="임차보증금 반환채무액(원)")
    default_days: int | None = Field(None, description="채무불이행 경과일수")
    enforcement_count: int | None = Field(None, description="강제집행·보전처분 신청 횟수")
    posted_date: str | None = Field(None, description="명단 게시일 (YYYY-MM-DD)")

class RegistrySummary(BaseModel):
    """위험진단에 사용되는 요약"""

    gap_section_status: str = Field(..., description="갑구 파싱 상태: EXTRACTED | PARSE_FAILED")
    eul_section_status: str = Field(
        ..., description="을구 파싱 상태: EXTRACTED | CONFIRMED_NONE(기록사항 없음 명시) | PARSE_FAILED"
    )
    seizure: str = Field(..., description="압류: TRUE | FALSE | UNKNOWN")
    provisional_seizure: str = Field(..., description="가압류: TRUE | FALSE | UNKNOWN")
    provisional_disposition: str = Field(..., description="가처분: TRUE | FALSE | UNKNOWN")
    auction_commenced: str = Field(..., description="경매개시결정(강제/임의 포함): TRUE | FALSE | UNKNOWN")
    trust_registration: str = Field(..., description="신탁등기: TRUE | FALSE | UNKNOWN")
    has_active_jeonse_right: str = Field(..., description="유효 전세권 존재: TRUE | FALSE | UNKNOWN")
    has_active_leasehold_registration: str = Field(..., description="유효 임차권등기 존재: TRUE | FALSE | UNKNOWN")
    active_mortgage_count: int | None = Field(
        None, description="유효 근저당 건수. 을구 파싱 실패: null"
    )
    total_active_max_claim_amount: int | None = Field(
        None, description="유효 근저당 채권최고액 합계(원)."
    )

class OcrRegisterResponse(BaseModel):
    """등기부등본 OCR/파싱 결과"""

    parse_status: str = Field(
        ..., description="SUCCESS | PARTIAL | NEEDS_REVIEW | FAILED", examples=["SUCCESS"]
    )
    parsed_at: str | None = Field(None, description="파싱 수행 시각 (ISO8601)")
    raw_address: str | None = Field(None, description="등본 표기 부동산 소재지 (소유자 주소와 다름)")
    property_address: str | None = Field(None, description="(구버전 호환) raw_address와 동일")
    issue_date: str | None = Field(None, description="열람/발급일 (YYYY-MM-DD) - 등본 최신성 판단용")
    current_owners: List[CurrentOwner] = Field(
        default_factory=list,
        description="현재(최종) 소유자 전원. 단독소유면 1명, 공유자(공동명의)면 2명 이상.",
    )
    ownership_history: List[OwnershipEntry] = Field(
        default_factory=list, description="소유권 이전 이력 전체 (등기 순서대로, 평면 리스트)"
    )
    rights: List[RightEntry] = Field(
        default_factory=list, description="갑구/을구 등기 항목 원본 전체 (순위번호 단위)"
    )
    mortgages: List[Mortgage] = Field(default_factory=list, description="근저당 개별 목록 (말소 포함)")
    jeonse_rights: List[DepositRight] = Field(default_factory=list, description="전세권 목록 (말소 포함)")
    leasehold_registrations: List[DepositRight] = Field(
        default_factory=list, description="임차권등기 목록 (말소 포함)"
    )
    summary: RegistrySummary = Field(..., description="위험진단용 요약")
    has_cancellation_mention: bool = Field(
        False, description="원문에 '말소' 단어가 있는지"
    )
    raw_text: str = Field(..., description="OCR/파싱에 사용된 원문 텍스트")
    source_type: str = Field(
        ...,
        description="텍스트를 얻은 경로",
        examples=["pdf_text", "pdf_ocr", "image_ocr", "image_ocr_multi"],
    )

class OwnerMatchResult(BaseModel):
    """소유자 1명에 대한 악성임대인 명단 대조 결과"""

    owner: CurrentOwner = Field(..., description="대조 대상 소유자")
    check_status: str = Field(
        ..., description="CHECKED(조회 수행됨) | NOT_CHECKED(조회 안 함) | ERROR(조회 실패)"
    )
    match_status: str = Field(
        ...,
        description="MATCH_HIGH(이름+나이 일치) | MATCH_NAME_ONLY(이름만 일치, 추가확인 필요) | "
                    "NO_MATCH(조회했고 명단에 없음) | UNKNOWN(미조회/조회오류 - NO_MATCH로 변환 금지)",
    )
    matched: bool | None = Field(
        None,
        description="true=매칭 확정 / false=조회했고 명단에 없음 / null=판단 불가",
    )
    match_type: str | None = Field(
        None, description="EXACT | MANUAL_REVIEW | null"
    )
    match_candidates: List[BadLandlordCandidate] = Field(
        default_factory=list, description="명단에서 걸린 후보 목록"
    )
    checked_at: str | None = Field(None, description="조회 시점 (ISO8601)")
    source: str = Field("HUG_상습채무불이행자명단", description="명단 출처")

class RegisterCheckResponse(BaseModel):
    """등기부등본 OCR + 악성임대인 명단 대조 최종 응답."""
 
    owner_info: OcrRegisterResponse = Field(..., description="등기부등본에서 뽑은 소유자 정보 전체")
    results: List[OwnerMatchResult] = Field(
        default_factory=list, description="소유자별 명단 대조 결과"
    )
    overall_match_status: str = Field(
        ...,
        description="results 중 가장 위험한 등급 (MATCH_HIGH > MATCH_NAME_ONLY > NO_MATCH)",
        examples=["MATCH_HIGH"],
    )