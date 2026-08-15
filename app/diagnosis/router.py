from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status

from app.diagnosis.schemas import (
    DiagnosisRequest,
    DiagnosisResponse,
    DiagnosisStatus,
    HousingType,
    IndicatorSummary,
    PropertyResolveRequest,
    PropertyResolveResponse,
    PropertySummary,
    RiskGrade,
    RiskSummary,
    ValuationSummary,
)


router = APIRouter(
    prefix="/internal/v1",
    tags=["diagnosis"],
)


def resolve_dummy_housing_type(address: str) -> HousingType:
    """
    실제 PropertyResolver가 구현되기 전까지 임시 판별 함수로 사용 중 .
    실제 서비스에서는 주소 정규화 및 건축물대장 조회로 교체할 예정.
    """

    if "오피스텔" in address:
        return HousingType.OFFICETEL

    if "연립" in address or "다세대" in address or "빌라" in address:
        return HousingType.VILLA

    if "단독" in address or "다가구" in address:
        return HousingType.DETACHED_MULTI

    return HousingType.APARTMENT


@router.post(
    "/properties/resolve",
    response_model=PropertyResolveResponse,
    status_code=status.HTTP_200_OK,
)
async def resolve_property(
    request: PropertyResolveRequest,
) -> PropertyResolveResponse:
    """
    주소 입력 단계에서 호출하는 dummy Property Resolve 앤드포인트.
    이 단계에서는 Diagnosis와 analysisId를 생성하지 않음.
    """

    normalized_address = " ".join(request.address.strip().split())
    housing_type = resolve_dummy_housing_type(normalized_address)

    return PropertyResolveResponse(
        normalizedAddress=normalized_address,
        housingType=housing_type,
        contractAreaRequired=(
            housing_type == HousingType.DETACHED_MULTI
        ),
    )


@router.post(
    "/diagnoses/analyze",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_diagnosis(
    request: DiagnosisRequest,
) -> DiagnosisResponse:
    """
    SpringBoot-FastAPI 연결 확인을 위한 dummy Analyze 앤드포인트.
    실제 구현 단계에서 고정값 생성 부분을 DiagnosisPipeline 호출로
    교체할 예정.
    """

    housing_type = resolve_dummy_housing_type(request.address)

    if (
        housing_type == HousingType.DETACHED_MULTI
        and request.contract_area is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CONTRACT_AREA_REQUIRED",
                "message": (
                    "전세 단독·다가구 분석에는 "
                    "계약 대상 공간의 면적이 필요합니다."
                ),
            },
        )

    estimated_sale_price = 300_000_000
    estimated_lease_price = 220_000_000
    active_mortgage_amount = 50_000_000

    lease_price_gap_rate = calculate_rate(
        numerator=request.deposit - estimated_lease_price,
        denominator=estimated_lease_price,
    )

    collateral_burden_amount = (
        active_mortgage_amount + request.deposit
    )

    collateral_burden_rate = calculate_rate(
        numerator=collateral_burden_amount,
        denominator=estimated_sale_price,
    )

    remaining_collateral_capacity = (
        estimated_sale_price - collateral_burden_amount
    )

    return DiagnosisResponse(
        analysisId=request.analysis_id,
        status=DiagnosisStatus.COMPLETED,
        analyzedAt=datetime.now(timezone.utc),
        property=PropertySummary(
            normalizedAddress=" ".join(
                request.address.strip().split()
            ),
            housingType=housing_type,
        ),
        valuation=ValuationSummary(
            estimatedSalePrice=estimated_sale_price,
            estimatedLeasePrice=estimated_lease_price,
        ),
        indicators=IndicatorSummary(
            leasePriceGapRate=lease_price_gap_rate,
            collateralBurdenRate=collateral_burden_rate,
            remainingCollateralCapacity=(
                remaining_collateral_capacity
            ),
        ),
        risk=RiskSummary(
            score=35,
            grade=RiskGrade.LOW,
        ),
        forcedWarnings=[],
        missingChecks=[],
        report=(
            "SpringBoot와 FastAPI 사이의 진단 API 연결 확인하려고 임시 분석 결과 넣음 제거 예정."
        ),
    )


def calculate_rate(
    numerator: int | Decimal,
    denominator: int | Decimal,
) -> float:
    """
    비율을 백분율 값으로 변환함. 예: 0.8333 → 83.33
    """

    if denominator <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RATE_DENOMINATOR",
                "message": "비율 계산 기준값은 0보다 커야 합니다.",
            },
        )

    return round(float(numerator / denominator) * 100, 2)