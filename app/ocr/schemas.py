from pydantic import BaseModel
from typing import Optional


class OwnershipEntry(BaseModel):
    name: str
    jumin_front: str
    address: str


class OcrRegisterResponse(BaseModel):
    current_owner_name: Optional[str] = None
    current_owner_address: Optional[str] = None
    current_owner_address_sigungu: Optional[str] = None
    ownership_history: list[OwnershipEntry] = []
    has_cancellation_mention: bool = False
    raw_text: str
    source_type: str  # "pdf_text" | "pdf_ocr" | "image_ocr"


class BadLandlordCandidate(BaseModel):
    name: str
    age: Optional[int] = None
    address: str
    address_sigungu: Optional[str] = None
    return_debt_amount: Optional[int] = None
    default_days: Optional[int] = None
    enforcement_count: Optional[int] = None
    posted_date: Optional[str] = None


class RegisterCheckResponse(BaseModel):
    owner: OcrRegisterResponse
    match_status: str  # "MATCH_HIGH" | "MATCH_NAME_ONLY" | "NO_MATCH"
    match_candidates: list[BadLandlordCandidate] = []
