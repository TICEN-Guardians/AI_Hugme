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


class ValuationReliability(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RegistryParseStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class RegistryParseConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class TriStateValue(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class WatchlistCheckStatus(str, Enum):
    CHECKED = "CHECKED"
    NOT_CHECKED = "NOT_CHECKED"
    ERROR = "ERROR"


class RegistryRiskPayload(ApiModel):
    parse_status: RegistryParseStatus = Field(alias="parseStatus")
    parse_confidence: RegistryParseConfidence = Field(alias="parseConfidence")
    total_active_max_claim_amount: int | None = Field(
        default=None,
        alias="totalActiveMaxClaimAmount",
        ge=0,
    )
    seizure: TriStateValue
    provisional_seizure: TriStateValue = Field(alias="provisionalSeizure")
    provisional_disposition: TriStateValue = Field(alias="provisionalDisposition")
    auction_commenced: TriStateValue = Field(alias="auctionCommenced")
    trust_registration: TriStateValue = Field(alias="trustRegistration")
    has_active_jeonse_right: TriStateValue = Field(alias="hasActiveJeonseRight")
    has_active_leasehold_registration: TriStateValue = Field(
        alias="hasActiveLeaseholdRegistration"
    )
    owner_matches_contract_party: TriStateValue = Field(
        default=TriStateValue.UNKNOWN,
        alias="ownerMatchesContractParty",
    )
    watchlist_check_status: WatchlistCheckStatus = Field(
        alias="watchlistCheckStatus"
    )
    bad_landlord_matched: bool | None = Field(
        default=None,
        alias="badLandlordMatched",
    )

class PropertySearchRequest(ApiModel):
    address: str = Field(
        min_length=1,
        max_length=500,
        description="사용자가 입력한 주소",
    )

class PropertyCandidate(ApiModel):
    building_name: str | None = Field(
        default=None,
        alias="buildingName",
    )
    dong_name: str | None = Field(
        default=None,
        alias="dongName",
    )
    housing_type: HousingType = Field(
        alias="housingType",
    )

class AddressCandidate(ApiModel):
    road_address: str = Field(
        alias="roadAddress",
    )
    jibun_address: str = Field(
        alias="jibunAddress",
    )
    building_name: str | None = Field(
        default=None,
        alias="buildingName",
    )


class PropertySearchResponse(ApiModel):
    normalized_address: str = Field(
        alias="normalizedAddress",
    )
    building_name: str | None = Field(
        default=None,
        alias="buildingName",
    )
    candidates: list[PropertyCandidate]
    address_candidates: list[AddressCandidate] = Field(
        default_factory=list,
        alias="addressCandidates",
    )

class PropertyResolveRequest(ApiModel):
    address: str = Field(
        min_length=1,
        max_length=500,
        description="사용자가 입력한 전체 주소",
    )
    dong_name: str | None = Field(
            default=None,
            alias="dongName",
            max_length=100,
            description="공동주택에서 사용자가 선택한 동",
        )
    ho_name: str | None = Field(
        default=None,
        alias="hoName",
        min_length=1,
        max_length=100,
    )

class PropertyResolveResponse(ApiModel):
    normalized_address: str = Field(
        alias="normalizedAddress",
        description="표준화된 주소",
    )
    building_name: str | None = Field(
            default=None,
            alias="buildingName",
    )
    dong_name: str | None = Field(
            default=None,
            alias="dongName",
    )
    ho_name: str | None = Field(
        default=None,
        alias="hoName",
    )
    housing_type: HousingType = Field(
        alias="housingType",
        description="서비스 모델 기준 주택유형",
    )
    contract_area_required: bool = Field(
        alias="contractAreaRequired",
        description="계약 대상 공간 면적의 사용자 입력 필요 여부",
    )
    unit_number_required: bool = Field(
        alias="unitNumberRequired",
    )
    exclusive_area: float | None = Field(
        default=None,
        alias="exclusiveArea",
    )
    common_area: float | None = Field(
        default=None,
        alias="commonArea",
    )
    total_area: float | None = Field(
        default=None,
        alias="totalArea",
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
    dong_name: str | None = Field(
        default=None,
        alias="dongName",
        max_length=100,
        description="공동주택에서 주소 검색 후 선택한 동",
    )
    ho_name: str | None = Field(
        default=None,
        alias="hoName",
        min_length=1,
        max_length=100,
        description="공동주택 전유부 조회용 호",
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
    exclusive_area: Decimal | None = Field(
        default=None,
        alias="exclusiveArea",
        gt=0,
        description="공동주택 사용자가 확인한 전용면적, ㎡",
    )
    floor: int = Field(
        description="사용자가 확인한 계약 대상 층",
    )
    registry_risk: RegistryRiskPayload | None = Field(
        default=None,
        alias="registryRisk",
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
    lease_to_sale_rate: float = Field(alias="leaseToSaleRate")
    lease_price_gap_rate: float = Field(
        alias="leasePriceGapRate",
        description="AI 예상 전세시세 대비 계약보증금 차이율",
    )
    collateral_burden_amount: int | None = Field(
        alias="collateralBurdenAmount"
    )
    collateral_burden_rate: float | None = Field(
        alias="collateralBurdenRate",
        description="매매가 대비 근저당과 계약보증금의 담보부담률",
    )
    recoverable_amount: int | None = Field(alias="recoverableAmount")
    deposit_shortfall: int | None = Field(alias="depositShortfall")
    remaining_collateral_capacity: int | None = Field(
        alias="remainingCollateralCapacity",
        description="AI 예상 매매가에서 담보부담금액을 뺀 금액, 원",
    )
    price_drop_scenarios: dict[str, float] | None = Field(
        alias="priceDropScenarios"
    )


class RiskBreakdown(ApiModel):
    underwater: int = Field(description="담보부족 위험(깡통전세)")
    rollover: int = Field(description="역전세 위험")
    property: int = Field(description="주택 특성 위험")
    market: int = Field(description="시장 상황 위험")


class RiskWeights(ApiModel):
    """위험요인별 만점. 클라이언트가 만점을 따로 갖지 않도록 함께 내려준다."""

    underwater: int
    rollover: int
    property: int
    market: int
    total: int


class RiskSummary(ApiModel):
    score: int = Field(
        ge=0,
        le=100,
        description="서비스 위험점수이며 전세사기 확률이 아님",
    )
    grade: RiskGrade
    breakdown: RiskBreakdown
    weights: RiskWeights
    grade_overridden: bool = Field(
        default=False,
        alias="gradeOverridden",
        description="강제 경고로 점수와 무관하게 등급이 상향됐는지 여부",
    )
    provisional_collateral_basis: bool = Field(
        default=False,
        alias="provisionalCollateralBasis",
        description="담보부담률을 확정하지 못해 전세가율을 대신 사용했는지 여부",
    )


class ReportMetric(ApiModel):
    key: str
    label: str
    value: int | float | str | None
    unit: str | None = None


class ReportSection(ApiModel):
    key: str
    title: str
    description: str
    metrics: list[ReportMetric] = Field(default_factory=list)


class ReportNotice(ApiModel):
    code: str
    title: str
    description: str
    severity: str


class RiskVerdict(str, Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    RISK = "RISK"


class PriceScenarioPoint(ApiModel):
    label: str
    price_drop_rate: int = Field(alias="priceDropRate")
    estimated_sale_price: int = Field(
        alias="estimatedSalePrice",
        ge=0,
        description="해당 하락률을 적용한 추정 매매가, 원",
    )
    collateral_burden_rate: float = Field(alias="collateralBurdenRate")
    verdict: RiskVerdict = Field(
        description="담보부담률 구간 판정. 임계값은 서버 규칙을 따른다.",
    )


class ReportFinding(ApiModel):
    title: str = Field(description="한 줄 제목")
    description: str = Field(description="근거 설명")


class ReportExplanation(ApiModel):
    summary: str
    key_findings: list[ReportFinding] = Field(alias="keyFindings")
    cautions: list[str]
    recommended_actions: list[str] = Field(alias="recommendedActions")
    generated_by: str = Field(alias="generatedBy")


class ReportDetail(ApiModel):
    title: str
    grade_label: str = Field(alias="gradeLabel")
    sections: list[ReportSection]
    notices: list[ReportNotice]
    price_scenarios: list[PriceScenarioPoint] = Field(alias="priceScenarios")
    explanation: ReportExplanation


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
    valuation_reliability: ValuationReliability = Field(
        alias="valuationReliability"
    )
    data_warnings: list[str] = Field(
        default_factory=list,
        alias="dataWarnings",
    )
    fallback_features: list[str] = Field(
        default_factory=list,
        alias="fallbackFeatures",
    )
    report: str
    report_detail: ReportDetail = Field(alias="reportDetail")
