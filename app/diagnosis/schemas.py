from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class DiagnosisMode(str, Enum):
    QUICK = "QUICK"
    DETAILED = "DETAILED"


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
    contract_party_name: str | None = Field(
        default=None,
        alias="contractPartyName",
        max_length=100,
        description="사용자가 입력한 계약 상대방(임대인) 이름",
    )
    owner_names: list[str] = Field(
        default_factory=list,
        alias="ownerNames",
        description="등기부에서 읽은 현재 소유자 이름",
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

class AddressSuggestionRequest(ApiModel):
    address: str = Field(min_length=2, max_length=500)


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


class AddressSuggestionResponse(ApiModel):
    candidates: list[AddressCandidate]


class PropertySearchResponse(ApiModel):
    normalized_address: str = Field(
        alias="normalizedAddress",
    )
    road_address: str | None = Field(
        default=None,
        alias="roadAddress",
    )
    jibun_address: str | None = Field(
        default=None,
        alias="jibunAddress",
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

class UnitAreaSnapshot(ApiModel):
    """전유부 면적 조회 결과 중 추론에 필요한 값만 담는다."""

    dong_name: str = Field(alias="dongName")
    ho_name: str = Field(alias="hoName")
    floor: int
    exclusive_area: float = Field(alias="exclusiveArea")
    common_area: float = Field(alias="commonArea")
    total_area: float = Field(alias="totalArea")


class PropertySnapshot(ApiModel):
    """properties/resolve 로 확보한 주소·건축물대장 정보를 담아 두는 그릇.

    analyze 가 같은 공공 API를 다시 부르지 않도록 이 값을 그대로 돌려받아 재사용한다.
    복원에 실패하면 기존처럼 다시 조회하므로, 형식이 어긋나도 진단은 계속된다.
    """

    road_address: str = Field(alias="roadAddress")
    jibun_address: str = Field(alias="jibunAddress")
    legal_dong_code: str = Field(alias="legalDongCode")
    district: str
    building_name: str | None = Field(default=None, alias="buildingName")

    sigungu_code: str = Field(alias="sigunguCode")
    bjdong_code: str = Field(alias="bjdongCode")
    plat_code: str = Field(alias="platCode")
    bun: str
    ji: str

    housing_type: HousingType = Field(alias="housingType")
    dong_name: str | None = Field(default=None, alias="dongName")
    ho_name: str | None = Field(default=None, alias="hoName")

    ledger_feature_values: dict[str, str | int | float | None] = Field(
        alias="ledgerFeatureValues",
        description="건축물대장 표제부에서 뽑은 Feature 값",
    )
    ledger_title: dict[str, str] = Field(
        alias="ledgerTitle",
        description="주택유형 세부 판정에 쓰는 표제부 원본 일부",
    )
    ledger_title_count: int = Field(default=0, alias="ledgerTitleCount")
    quality_blocking: list[str] = Field(
        default_factory=list,
        alias="qualityBlocking",
    )
    quality_warnings: list[str] = Field(
        default_factory=list,
        alias="qualityWarnings",
    )
    unit_area: UnitAreaSnapshot | None = Field(default=None, alias="unitArea")


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
    property_snapshot: PropertySnapshot = Field(
        alias="propertySnapshot",
        description="analyze 에 그대로 돌려주면 공공 API 재조회를 건너뛴다.",
    )

class DiagnosisRequest(ApiModel):
    analysis_id: int = Field(
        alias="analysisId",
        gt=0,
        description="SpringBoot에서 발급한 분석 식별자",
    )
    mode: DiagnosisMode
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
    floor: int | None = Field(
        default=None,
        description=(
            "사용자가 확인한 계약 대상 층. "
            "단독·다가구 모델에는 층 Feature가 없어 값이 없어도 된다."
        ),
    )
    registry_risk: RegistryRiskPayload | None = Field(
        default=None,
        alias="registryRisk",
    )
    property_snapshot: PropertySnapshot | None = Field(
        default=None,
        alias="propertySnapshot",
        description=(
            "properties/resolve 결과. 있으면 주소·건축물대장 재조회를 건너뛴다. "
            "없거나 복원에 실패하면 기존처럼 다시 조회한다."
        ),
    )

    @model_validator(mode="after")
    def validate_registry_by_mode(self):
        if self.mode == DiagnosisMode.QUICK and self.registry_risk is not None:
            raise ValueError("간편진단에는 등기 권리정보를 포함할 수 없습니다")
        if self.mode == DiagnosisMode.DETAILED and self.registry_risk is None:
            raise ValueError("정밀진단에는 등기 권리정보가 필요합니다")
        return self


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
    price_burden: int = Field(alias="priceBurden")
    lease_market_deviation: int = Field(alias="leaseMarketDeviation")
    market_trend: int = Field(alias="marketTrend")
    policy_adjustment: int = Field(alias="policyAdjustment")
    rights_adjustment: int = Field(alias="rightsAdjustment")


class RiskWeights(ApiModel):
    price_burden: int = Field(alias="priceBurden")
    lease_market_deviation: int = Field(alias="leaseMarketDeviation")
    market_trend: int = Field(alias="marketTrend")
    total: int


class RiskSummary(ApiModel):
    score: int = Field(
        ge=0,
        le=100,
        description="서비스 위험점수이며 전세사기 확률이 아님",
    )
    base_score: int = Field(alias="baseScore", ge=0, le=100)
    grade: RiskGrade
    breakdown: RiskBreakdown
    weights: RiskWeights
    score_floor: int | None = Field(default=None, alias="scoreFloor")
    floor_reasons: list[str] = Field(default_factory=list, alias="floorReasons")
    score_floor_applied: bool = Field(
        default=False,
        alias="scoreFloorApplied",
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


class ReportAction(ApiModel):
    label: str = Field(description="목록에 쓰는 명사형 요약")
    description: str = Field(description="계약자가 실행할 문장")


class ReportExplanation(ApiModel):
    summary: str
    key_findings: list[ReportFinding] = Field(alias="keyFindings")
    cautions: list[str]
    recommended_actions: list[ReportAction] = Field(alias="recommendedActions")
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
    mode: DiagnosisMode
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
