from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """
    SpringBoot와 주고받는 JSON 필드명을 camelCase로 유지하기 위한
    공통 Pydantic 모델.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )


class HousingType(str, Enum):
    APARTMENT = "APARTMENT"
    VILLA = "VILLA"
    OFFICETEL = "OFFICETEL"
    DETACHED_MULTI = "DETACHED_MULTI"


class DiagnosisStatus(str, Enum):
    COMPLETED = "COMPLETED"


class RiskGrade(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PropertyResolveRequest(ApiModel):
    address: str = Field(
        min_length=1,
        max_length=500,
        description="사용자가 입력한 전체 주소",
        examples=["서울특별시 송파구 잠실동 123 101동 402호"],
    )


class PropertyResolveResponse(ApiModel):
    normalized_address: str = Field(
        alias="normalizedAddress",
        description="표준화된 주소",
    )
    housing_type: HousingType = Field(
        alias="housingType",
        description="서비스 모델 기준 주택유형",
    )
    contract_area_required: bool = Field(
        alias="contractAreaRequired",
        description="계약 대상 공간 면적의 사용자 입력 필요 여부",
    )


class DiagnosisRequest(ApiModel):
    analysis_id: int = Field(
        alias="analysisId",
        gt=0,
        description="SpringBoot에서 발급한 분석 식별자",
    )
    address: str = Field(
        min_length=1,
        max_length=500,
        description="진단 대상 전체 주소",
    )
    deposit: int = Field(
        gt=0,
        description="계약 예정 전세보증금, 원 단위",
    )
    contract_date: date = Field(
        alias="contractDate",
        description="계약 예정일",
    )
    contract_area: Decimal | None = Field(
        default=None,
        alias="contractArea",
        gt=0,
        description="전세 단독·다가구의 계약 대상 공간 면적, ㎡",
    )


class PropertySummary(ApiModel):
    normalized_address: str = Field(alias="normalizedAddress")
    housing_type: HousingType = Field(alias="housingType")


class ValuationSummary(ApiModel):
    estimated_sale_price: int = Field(
        alias="estimatedSalePrice",
        ge=0,
        description="AI 예상 총매매가격, 원",
    )
    estimated_lease_price: int = Field(
        alias="estimatedLeasePrice",
        ge=0,
        description="AI 예상 총전세보증금, 원",
    )


class IndicatorSummary(ApiModel):
    lease_price_gap_rate: float = Field(
        alias="leasePriceGapRate",
        description="AI 예상 전세시세 대비 계약보증금 차이율",
    )
    collateral_burden_rate: float = Field(
        alias="collateralBurdenRate",
        description="매매가 대비 근저당과 계약보증금의 담보부담률",
    )
    remaining_collateral_capacity: int = Field(
        alias="remainingCollateralCapacity",
        description="AI 예상 매매가에서 담보부담금액을 뺀 금액, 원",
    )


class RiskSummary(ApiModel):
    score: int = Field(
        ge=0,
        le=100,
        description="서비스 위험점수이며 전세사기 확률이 아님",
    )
    grade: RiskGrade


class DiagnosisResponse(ApiModel):
    analysis_id: int = Field(alias="analysisId")
    status: DiagnosisStatus
    analyzed_at: datetime = Field(alias="analyzedAt")

    property: PropertySummary
    valuation: ValuationSummary
    indicators: IndicatorSummary
    risk: RiskSummary

    forced_warnings: list[str] = Field(
        default_factory=list,
        alias="forcedWarnings",
    )
    missing_checks: list[str] = Field(
        default_factory=list,
        alias="missingChecks",
    )
    report: str