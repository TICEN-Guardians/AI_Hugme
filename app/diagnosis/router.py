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
from app.diagnosis.property_address_service import (PropertyAddressService,)
from app.diagnosis.property_search_service import (PropertySearchService,)
from app.diagnosis.schemas import (
    DiagnosisRequest,
    DiagnosisResponse,
    DiagnosisStatus,
    HousingType,
    IndicatorSummary,
    PropertyResolveRequest,
    PropertyResolveResponse,
    PropertySummary,
    RiskBreakdown,
    RiskSummary,
    RiskWeights,
    ValuationReliability,
    ValuationSummary,
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
    final_grade = result.forced_warning.grade
    reliability = valuation_reliability(result)
    report_detail = explain_report(
        build_report_detail(request, result, reliability)
    )

    return DiagnosisResponse(
        analysisId=request.analysis_id,
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
        risk=RiskSummary(
            score=score.total,
            grade=final_grade,
            breakdown=RiskBreakdown(
                underwater=score.underwater,
                rollover=score.rollover,
                property=score.property,
                market=score.market,
            ),
            weights=RiskWeights(
                underwater=RiskRule.LIMITS["underwater"],
                rollover=RiskRule.LIMITS["rollover"],
                property=RiskRule.LIMITS["property"],
                market=RiskRule.LIMITS["market"],
                total=sum(RiskRule.LIMITS.values()),
            ),
            gradeOverridden=result.forced_warning.grade_overridden,
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


def valuation_reliability(result) -> ValuationReliability:
    if result.fallback_features:
        return ValuationReliability.LOW
    if result.warnings:
        return ValuationReliability.MEDIUM
    return ValuationReliability.HIGH
