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
