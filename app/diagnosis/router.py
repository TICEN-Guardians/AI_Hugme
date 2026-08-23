from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from app.config import settings
from app.diagnosis.external.address.client import (AddressApiError,AddressClient,)
from app.diagnosis.external.address.mapper import (AddressMappingError,)
from app.diagnosis.external.address.service import (AddressResolutionError,AddressService,)
from app.diagnosis.external.building_ledger.client import (BuildingLedgerApiError,BuildingLedgerClient,)
from app.diagnosis.external.building_ledger.selector import (BuildingLedgerSelectionError,)
from app.diagnosis.external.building_ledger.service import (BuildingLedgerService,)
from app.diagnosis.housing_type_resolver import (HousingTypeResolutionError,)
from app.diagnosis.diagnosis_dependencies import get_diagnosis_pipeline
from app.diagnosis.deposit_recommendation import (
    DepositRecommendationCalculator,
)
from app.diagnosis.what_if import (
    DiagnosisWhatIfCalculator,
    WhatIfScenarioResult,
)
from app.diagnosis.property_address_service import (PropertyAddressService,)
from app.diagnosis.property_search_service import (PropertySearchService,)
from app.diagnosis.property_snapshot import build_property_snapshot
from app.diagnosis.schemas import (
    AddressSuggestionRequest,
    AddressSuggestionResponse,
    DiagnosisRequest,
    DiagnosisResponse,
    DiagnosisStatus,
    DiagnosisWhatIfRequest,
    DiagnosisWhatIfResponse,
    DepositRecommendationSummary,
    HousingType,
    IndicatorSummary,
    MarketComparableBin,
    MarketComparableSummary,
    PropertyResolveRequest,
    PropertyResolveResponse,
    PropertySummary,
    RiskBreakdown,
    RiskSummary,
    RiskWeights,
    ValuationReliability,
    ValuationSummary,
    WhatIfScenarioSummary,
    AddressCandidate,PropertyCandidate,
    PropertySearchRequest,
    PropertySearchResponse,
)
from app.diagnosis.external.building_ledger.unit_area import (UnitAreaError,)
from app.diagnosis.risk_rule import RiskRule
from app.diagnosis.report_builder import build_report_detail
from app.diagnosis.report_explainer import explain_report

router = APIRouter(
    prefix="/internal/v1",
    tags=["diagnosis"],
)
def create_address_service() -> AddressService:
    client = AddressClient(
        confirmation_key=(
            settings.address_api_confirmation_key
        ),
        timeout=settings.address_api_timeout,
    )

    return AddressService(client)


def create_building_ledger_client(
) -> BuildingLedgerClient:
    return BuildingLedgerClient(
        service_key=settings.building_ledger_api_key,
        timeout=settings.building_ledger_api_timeout,
    )


def create_property_search_service(
) -> PropertySearchService:
    return PropertySearchService(
        address_service=create_address_service(),
        building_ledger_client=(
            create_building_ledger_client()
        ),
    )


def create_property_address_service(
) -> PropertyAddressService:
    ledger_client = create_building_ledger_client()

    return PropertyAddressService(
        address_service=create_address_service(),
        building_ledger_service=(
            BuildingLedgerService(ledger_client)
        ),
    )

def property_http_exception(
    exc: Exception,
) -> HTTPException:
    external_errors = (
        AddressApiError,
        BuildingLedgerApiError,
    )

    if isinstance(exc, external_errors):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "PROPERTY_EXTERNAL_API_ERROR",
                "message": str(exc),
            },
        )

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "PROPERTY_RESOLUTION_FAILED",
            "message": str(exc),
        },
    )

@router.post(
    "/properties/search",
    response_model=PropertySearchResponse,
    status_code=status.HTTP_200_OK,
)
def search_property(
    request: PropertySearchRequest,
) -> PropertySearchResponse:
    try:
        result = (
            create_property_search_service()
            .search(request.address)
        )
    except (
        AddressApiError,
        AddressMappingError,
        AddressResolutionError,
        BuildingLedgerApiError,
    ) as exc:
        raise property_http_exception(exc) from None

    candidates = [
        PropertyCandidate(
            buildingName=item.building_name,
            dongName=item.dong_name,
            housingType=item.housing_type,
        )
        for item in result.candidates
    ]

    return PropertySearchResponse(
        normalizedAddress=result.normalized_address,
        roadAddress=result.road_address,
        jibunAddress=result.jibun_address,
        buildingName=result.building_name,
        candidates=candidates,
        addressCandidates=[
            AddressCandidate(
                roadAddress=item.road_address,
                jibunAddress=item.jibun_address,
                buildingName=item.building_name,
            )
            for item in result.address_candidates
        ],
    )


@router.post(
    "/properties/suggestions",
    response_model=AddressSuggestionResponse,
    status_code=status.HTTP_200_OK,
)
def suggest_address(
    request: AddressSuggestionRequest,
) -> AddressSuggestionResponse:
    try:
        candidates = create_property_search_service().suggest(request.address)
    except (AddressApiError, ValueError) as exc:
        raise property_http_exception(exc) from None

    return AddressSuggestionResponse(
        candidates=[
            AddressCandidate(
                roadAddress=item.road_address,
                jibunAddress=item.jibun_address,
                buildingName=item.building_name,
            )
            for item in candidates
        ]
    )


@router.post(
    "/properties/resolve",
    response_model=PropertyResolveResponse,
    status_code=status.HTTP_200_OK,
)
def resolve_property(
    request: PropertyResolveRequest,
) -> PropertyResolveResponse:
    try:
        result = (
            create_property_address_service()
            .resolve(
                address=request.address,
                dong_name=request.dong_name,
                ho_name=request.ho_name,
            )
        )
    except (
        AddressApiError,
        AddressMappingError,
        AddressResolutionError,
        BuildingLedgerApiError,
        BuildingLedgerSelectionError,
        HousingTypeResolutionError,
        UnitAreaError,
    ) as exc:
        raise property_http_exception(exc) from None

    unit_area = result.unit_area
    selected_building_name = str(
        result.building_ledger.selected_title.get("bldNm")
        or ""
    ).strip() or None

    return PropertyResolveResponse(
        normalizedAddress=result.address.road_address,
        buildingName=(
            result.address.building_name
            or selected_building_name
        ),
        dongName=result.dong_name,
        hoName=result.ho_name,
        housingType=result.housing_type,
        contractAreaRequired=(
            result.housing_type
            == HousingType.DETACHED_MULTI
        ),
        unitNumberRequired=(
            result.housing_type
            != HousingType.DETACHED_MULTI
            and not result.ho_name
        ),
        exclusiveArea=(
            unit_area.exclusive_area
            if unit_area else None
        ),
        commonArea=(
            unit_area.common_area
            if unit_area else None
        ),
        totalArea=(
            unit_area.total_area
            if unit_area else None
        ),
        # analyze 가 이 값을 그대로 돌려주면 공공 API를 다시 부르지 않는다.
        propertySnapshot=build_property_snapshot(result),
    )

@router.post(
    "/diagnoses/analyze",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_diagnosis(
    request: DiagnosisRequest,
) -> DiagnosisResponse:
    try:
        result = get_diagnosis_pipeline().analyze(request)
    except (
        AddressApiError,
        AddressMappingError,
        AddressResolutionError,
        BuildingLedgerApiError,
        BuildingLedgerSelectionError,
        HousingTypeResolutionError,
        UnitAreaError,
    ) as exc:
        raise property_http_exception(exc) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "DIAGNOSIS_ANALYSIS_FAILED",
                "message": str(exc),
            },
        ) from None

    indicators = result.risk_indicators
    score = result.risk_score
    final_score = result.forced_warning.score
    final_grade = result.forced_warning.grade
    score_floor = max(
        (
            value
            for value in (score.policy_floor, result.forced_warning.score_floor)
            if value is not None
        ),
        default=None,
    )
    active_max_claim_amount = (
        indicators.collateral_burden_amount - request.deposit
        if indicators.collateral_burden_amount is not None
        else None
    )
    deposit_recommendation = DepositRecommendationCalculator.calculate(
        mode=request.mode,
        estimated_sale_price=result.estimated_sale_price,
        estimated_lease_price=result.estimated_lease_price,
        current_deposit=request.deposit,
        active_max_claim_amount=active_max_claim_amount,
        severity=result.risk_severity.severity,
        unresolved_risk_reasons=result.forced_warning.floor_reasons,
    )
    reliability = valuation_reliability(result)
    report_detail = explain_report(
        build_report_detail(request, result, reliability)
    )

    return DiagnosisResponse(
        analysisId=request.analysis_id,
        mode=request.mode,
        status=DiagnosisStatus.COMPLETED,
        analyzedAt=datetime.now(timezone.utc),
        property=PropertySummary(
            normalizedAddress=result.normalized_address,
            housingType=result.housing_type,
        ),
        valuation=ValuationSummary(
            estimatedSalePrice=result.estimated_sale_price,
            estimatedLeasePrice=result.estimated_lease_price,
        ),
        marketComparables=MarketComparableSummary(
            status=result.market_comparables.status,
            source=result.market_comparables.source,
            scope=result.market_comparables.scope,
            sampleCount=result.market_comparables.sample_count,
            periodStart=result.market_comparables.period_start,
            periodEnd=result.market_comparables.period_end,
            areaMin=result.market_comparables.area_min,
            areaMax=result.market_comparables.area_max,
            minimum=result.market_comparables.minimum,
            percentile25=result.market_comparables.percentile_25,
            median=result.market_comparables.median,
            percentile75=result.market_comparables.percentile_75,
            maximum=result.market_comparables.maximum,
            userDepositPercentile=(
                result.market_comparables.user_deposit_percentile
            ),
            bins=[
                MarketComparableBin(
                    lowerBound=item.lower_bound,
                    upperBound=item.upper_bound,
                    count=item.count,
                )
                for item in result.market_comparables.bins
            ],
            warnings=list(
                result.market_comparables.warnings
            ),
        ),
        indicators=IndicatorSummary(
            leaseToSaleRate=round(indicators.lease_to_sale_rate * 100, 2),
            leasePriceGapRate=round(indicators.lease_price_gap_rate * 100, 2),
            collateralBurdenAmount=indicators.collateral_burden_amount,
            collateralBurdenRate=(
                round(indicators.collateral_burden_rate * 100, 2)
                if indicators.collateral_burden_rate is not None
                else None
            ),
            recoverableAmount=indicators.recoverable_amount,
            depositShortfall=indicators.deposit_shortfall,
            remainingCollateralCapacity=(indicators.remaining_collateral_capacity),
            priceDropScenarios=(
                {
                    name: round(value * 100, 2)
                    for name, value in indicators.price_drop_scenarios.items()
                }
                if indicators.price_drop_scenarios is not None
                else None
            ),
        ),
        depositRecommendation=DepositRecommendationSummary(
            recommendedLimit=deposit_recommendation.recommended_limit,
            currentDeposit=request.deposit,
            reductionRequired=deposit_recommendation.reduction_required,
            withinRecommendedLimit=(
                deposit_recommendation.within_recommended_limit
            ),
            targetScoreMax=deposit_recommendation.target_score_max,
            targetGrade=deposit_recommendation.target_grade,
            scoreAtLimit=deposit_recommendation.score_at_limit,
            calculationBasis=deposit_recommendation.calculation_basis,
            registryReflected=deposit_recommendation.registry_reflected,
            provisional=deposit_recommendation.provisional,
            adjustmentCanResolveFinalRisk=(
                deposit_recommendation.adjustment_can_resolve_final_risk
            ),
            unresolvedRiskReasons=list(
                deposit_recommendation.unresolved_risk_reasons
            ),
        ),
        risk=RiskSummary(
            score=final_score,
            baseScore=score.base_total,
            grade=final_grade,
            breakdown=RiskBreakdown(
                priceBurden=score.price_burden,
                leaseMarketDeviation=score.lease_market_deviation,
                marketTrend=score.market_trend,
                policyAdjustment=score.policy_adjustment,
                rightsAdjustment=final_score - score.total,
            ),
            weights=RiskWeights(
                priceBurden=RiskRule.LIMITS["price_burden"],
                leaseMarketDeviation=RiskRule.LIMITS["lease_market_deviation"],
                marketTrend=RiskRule.LIMITS["market_trend"],
                total=sum(RiskRule.LIMITS.values()),
            ),
            scoreFloor=score_floor,
            floorReasons=list(
                dict.fromkeys(
                    (*score.floor_reasons, *result.forced_warning.floor_reasons)
                )
            ),
            scoreFloorApplied=final_score != score.base_total,
            provisionalCollateralBasis=score.provisional_collateral_basis,
        ),
        forcedWarnings=list(result.forced_warning.warnings),
        missingChecks=list(result.missing_checks),
        valuationReliability=reliability,
        dataWarnings=list(result.warnings),
        fallbackFeatures=list(result.fallback_features),
        report=f"규칙 기반 전세 위험등급은 {final_grade.value}입니다.",
        reportDetail=report_detail,
    )



@router.post(
    "/diagnoses/what-if",
    response_model=DiagnosisWhatIfResponse,
    status_code=status.HTTP_200_OK,
)
def calculate_diagnosis_what_if(
    request: DiagnosisWhatIfRequest,
) -> DiagnosisWhatIfResponse:
    try:
        result = DiagnosisWhatIfCalculator.calculate(
            mode=request.mode,
            estimated_sale_price=request.estimated_sale_price,
            estimated_lease_price=request.estimated_lease_price,
            baseline_deposit=request.baseline_deposit,
            scenario_deposit=request.scenario_deposit,
            sale_price_drop_rate=request.sale_price_drop_rate,
            lease_price_drop_rate=request.lease_price_drop_rate,
            active_max_claim_amount=request.active_max_claim_amount,
            scenario_active_max_claim_amount=(
                request.scenario_active_max_claim_amount
            ),
            remove_active_mortgage=request.remove_active_mortgage,
            market_trend_score=request.market_trend_score,
            unresolved_risk_reasons=tuple(
                request.unresolved_risk_reasons
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "DIAGNOSIS_WHAT_IF_FAILED",
                "message": str(exc),
            },
        ) from None

    recommendation = result.deposit_recommendation
    return DiagnosisWhatIfResponse(
        baseline=what_if_scenario_summary(result.baseline),
        scenario=what_if_scenario_summary(result.scenario),
        scoreChange=result.score_change,
        gradeChanged=result.grade_changed,
        registryBlockersRemain=result.registry_blockers_remain,
        unresolvedRiskReasons=list(result.unresolved_risk_reasons),
        depositRecommendation=DepositRecommendationSummary(
            recommendedLimit=recommendation.recommended_limit,
            currentDeposit=result.scenario.deposit,
            reductionRequired=recommendation.reduction_required,
            withinRecommendedLimit=recommendation.within_recommended_limit,
            targetScoreMax=recommendation.target_score_max,
            targetGrade=recommendation.target_grade,
            scoreAtLimit=recommendation.score_at_limit,
            calculationBasis=recommendation.calculation_basis,
            registryReflected=recommendation.registry_reflected,
            provisional=recommendation.provisional,
            adjustmentCanResolveFinalRisk=(
                recommendation.adjustment_can_resolve_final_risk
            ),
            unresolvedRiskReasons=list(
                recommendation.unresolved_risk_reasons
            ),
        ),
    )


def what_if_scenario_summary(
    result: WhatIfScenarioResult,
) -> WhatIfScenarioSummary:
    indicators = result.indicators
    score = result.score
    return WhatIfScenarioSummary(
        valuation=ValuationSummary(
            estimatedSalePrice=result.estimated_sale_price,
            estimatedLeasePrice=result.estimated_lease_price,
        ),
        deposit=result.deposit,
        activeMaxClaimAmount=result.active_max_claim_amount,
        indicators=IndicatorSummary(
            leaseToSaleRate=round(indicators.lease_to_sale_rate * 100, 2),
            leasePriceGapRate=round(
                indicators.lease_price_gap_rate * 100,
                2,
            ),
            collateralBurdenAmount=indicators.collateral_burden_amount,
            collateralBurdenRate=(
                round(indicators.collateral_burden_rate * 100, 2)
                if indicators.collateral_burden_rate is not None
                else None
            ),
            recoverableAmount=indicators.recoverable_amount,
            depositShortfall=indicators.deposit_shortfall,
            remainingCollateralCapacity=(
                indicators.remaining_collateral_capacity
            ),
            priceDropScenarios=(
                {
                    name: round(value * 100, 2)
                    for name, value in indicators.price_drop_scenarios.items()
                }
                if indicators.price_drop_scenarios is not None
                else None
            ),
        ),
        risk=RiskSummary(
            score=result.final_score,
            baseScore=score.base_total,
            grade=result.final_grade,
            breakdown=RiskBreakdown(
                priceBurden=score.price_burden,
                leaseMarketDeviation=score.lease_market_deviation,
                marketTrend=score.market_trend,
                policyAdjustment=score.policy_adjustment,
                rightsAdjustment=result.rights_adjustment,
            ),
            weights=RiskWeights(
                priceBurden=RiskRule.LIMITS["price_burden"],
                leaseMarketDeviation=RiskRule.LIMITS[
                    "lease_market_deviation"
                ],
                marketTrend=RiskRule.LIMITS["market_trend"],
                total=sum(RiskRule.LIMITS.values()),
            ),
            scoreFloor=result.score_floor,
            floorReasons=list(result.floor_reasons),
            scoreFloorApplied=result.final_score != score.base_total,
            provisionalCollateralBasis=score.provisional_collateral_basis,
        ),
    )

def valuation_reliability(result) -> ValuationReliability:
    if result.fallback_features:
        return ValuationReliability.LOW
    if result.warnings:
        return ValuationReliability.MEDIUM
    return ValuationReliability.HIGH
