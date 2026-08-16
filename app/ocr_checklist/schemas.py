from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HousingTypeCode(str, Enum):
    """주택 유형."""

    APARTMENT = "APARTMENT"
    OFFICETEL = "OFFICETEL"
    VILLA = "VILLA"
    HOUSE = "HOUSE"


class ContractType(str, Enum):
    """계약 유형."""

    NEW = "NEW"
    RENEWAL = "RENEWAL"


class PartyType(str, Enum):
    """임대인·임차인 유형."""

    PERSON = "PERSON"
    COMPANY = "COMPANY"


HOUSING_TYPE_NAMES = {
    HousingTypeCode.APARTMENT: "아파트",
    HousingTypeCode.OFFICETEL: "오피스텔",
    HousingTypeCode.VILLA: "빌라",
    HousingTypeCode.HOUSE: "주택",
}


class MaskRegion(BaseModel):
    """LLM 전송 전에 검정색으로 가릴 이미지 영역."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(0, ge=0, description="0부터 시작하는 PDF/이미지 페이지 번호")
    x1: float = Field(..., ge=0)
    y1: float = Field(..., ge=0)
    x2: float = Field(..., ge=0)
    y2: float = Field(..., ge=0)
    referenceWidth: float | None = Field(
        None,
        gt=0,
        description="픽셀 좌표를 측정한 기준 이미지 너비",
    )
    referenceHeight: float | None = Field(
        None,
        gt=0,
        description="픽셀 좌표를 측정한 기준 이미지 높이",
    )

    @model_validator(mode="after")
    def validate_region(self):
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("x2/y2는 x1/y1보다 커야 합니다.")

        has_reference_width = self.referenceWidth is not None
        has_reference_height = self.referenceHeight is not None
        if has_reference_width != has_reference_height:
            raise ValueError(
                "referenceWidth와 referenceHeight는 함께 입력해야 합니다."
            )

        if has_reference_width and (
            self.x2 > self.referenceWidth
            or self.y2 > self.referenceHeight
        ):
            raise ValueError("마스킹 좌표가 기준 이미지 크기를 벗어났습니다.")

        if not has_reference_width and max(self.x1, self.y1, self.x2, self.y2) <= 1:
            return self

        return self


class ChecklistFields(BaseModel):
    """Spring 체크리스트 API가 받는 최종 9개 필드."""

    model_config = ConfigDict(extra="forbid")

    housingTypeCode: HousingTypeCode = Field(
        HousingTypeCode.APARTMENT,
        description="APARTMENT | OFFICETEL | VILLA | HOUSE",
    )
    housingTypeName: str = Field(
        "아파트",
        description="아파트 | 오피스텔 | 빌라 | 주택",
    )
    contractAddress: str | None = Field(
        None,
        description="소재지와 상세주소를 합친 계약 주소",
    )
    contractType: ContractType = Field(
        ContractType.NEW,
        description="NEW | RENEWAL",
    )
    tenantType: PartyType = Field(
        PartyType.PERSON,
        description="PERSON | COMPANY",
    )
    landlordType: PartyType = Field(
        PartyType.PERSON,
        description="PERSON | COMPANY",
    )
    fixedDateConfirmed: bool = False
    officetelResidentialMarked: bool = False
    landlordProxyContract: bool = False

    @model_validator(mode="after")
    def normalize_fields(self):
        self.housingTypeName = HOUSING_TYPE_NAMES[self.housingTypeCode]

        if self.contractAddress:
            self.contractAddress = " ".join(self.contractAddress.split())

        if self.housingTypeCode != HousingTypeCode.OFFICETEL:
            self.officetelResidentialMarked = False

        return self


class LlmChecklistResult(ChecklistFields):
    """OpenAI 구조화 출력 형식."""


class OcrChecklistResponse(ChecklistFields):
    """POST /checklist/ocr 응답 형식."""
