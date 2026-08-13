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
    """현재(최종) 소유자 1명 - 공유자면 이게 여러 개 배열로 옴."""
 
    name: str = Field(..., description="소유자 성명")
    jumin_front: str = Field(..., description="주민등록번호 앞자리")
    address: str = Field(..., description="주소 원문")
    age: int | None = Field(None, description="주민번호 앞자리에서 역산한 나이(오늘 기준)")

class OcrRegisterResponse(BaseModel):
    """등기부등본 OCR/파싱 결과."""
 
    current_owners: List[CurrentOwner] = Field(
        default_factory=list,
        description="현재(최종) 소유자 전원. 단독소유면 1명, 공유자(공동명의)면 2명 이상.",
    )
    ownership_history: List[OwnershipEntry] = Field(
        default_factory=list, description="소유권 이전 이력 전체 (등기 순서대로, 평면 리스트)"
    )
    has_cancellation_mention: bool = Field(
        False, description="원문에 '말소' 언급이 있는지 여부 (사람 재확인 권장 플래그)"
    )
    raw_text: str = Field(..., description="OCR/파싱에 사용된 원문 텍스트")
    source_type: str = Field(
        ...,
        description="텍스트를 얻은 경로",
        examples=["pdf_text", "pdf_ocr", "image_ocr", "image_ocr_multi"],
    )


class BadLandlordCandidate(BaseModel):
    """HUG 상습채무불이행자 명단에서 조회된 후보 1건."""

    name: str = Field(..., description="성명")
    age: int | None = Field(None, description="나이(법인 임대인은 None)")
    address: str = Field(..., description="주소 원문")
    address_sigungu: str | None = Field(None, description="시/군/구")
    return_debt_amount: int | None = Field(None, description="임차보증금 반환채무액(원)")
    default_days: int | None = Field(None, description="채무불이행 경과일수")
    enforcement_count: int | None = Field(None, description="강제집행·보전처분 신청 횟수")
    posted_date: str | None = Field(None, description="명단 게시일 (YYYY-MM-DD)")

class OwnerMatchResult(BaseModel):
    """소유자 1명에 대한 명단 대조 결과."""
 
    owner: CurrentOwner = Field(..., description="대조 대상 소유자")
    match_status: str = Field(
        ..., description="MATCH_HIGH | MATCH_NAME_ONLY | NO_MATCH", examples=["MATCH_HIGH"]
    )
    match_candidates: List[BadLandlordCandidate] = Field(
        default_factory=list, description="명단에서 걸린 후보 목록"
    )

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