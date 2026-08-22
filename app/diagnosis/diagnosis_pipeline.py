import logging
from dataclasses import dataclass
from decimal import Decimal

from app.diagnosis.feature_sources import UNAVAILABLE_FEATURE_WARNINGS
from app.diagnosis.market_feature_service import MarketFeatureService
from app.diagnosis.forced_warning import ForcedWarningResult, ForcedWarningRule
from app.diagnosis.model.model_predictor import ModelPredictor
from app.diagnosis.model.target_transform import PredictionResult
from app.diagnosis.property_address_service import (
    PropertyAddressResult,
    PropertyAddressService,
)
from app.diagnosis.property_feature_factory import PropertyFeatureFactory
from app.diagnosis.property_matcher import PropertyMatcher
from app.diagnosis.property_snapshot import (
    matches_request,
    restore_property_address_result,
)
from app.diagnosis.registry_risk_adapter import RegistryRiskAdapter
from app.diagnosis.risk_indicator import (
    RiskIndicatorCalculator,
    RiskIndicatorResult,
)
from app.diagnosis.risk_rule import RiskRule, RiskScoreResult
from app.diagnosis.risk_severity_factory import (
    RiskSeverityFactory,
    RiskSeverityResult,
)
from app.diagnosis.schemas import DiagnosisMode, DiagnosisRequest, HousingType


logger = logging.getLogger(__name__)

MODEL_TYPES = {
    HousingType.APARTMENT: "아파트",
    HousingType.VILLA: "연립다세대",
    HousingType.OFFICETEL: "오피스텔",
    HousingType.DETACHED_MULTI: "단독다가구",
}


@dataclass(frozen=True)
class DiagnosisPipelineResult:
    normalized_address: str
    housing_type: HousingType
    sale: PredictionResult
    lease: PredictionResult
    estimated_sale_price: int
    estimated_lease_price: int
    risk_indicators: RiskIndicatorResult
    risk_severity: RiskSeverityResult
    risk_score: RiskScoreResult
    forced_warning: ForcedWarningResult
    warnings: tuple[str, ...]
    missing_checks: tuple[str, ...]
    fallback_features: tuple[str, ...]


class DiagnosisPipeline:
    def __init__(
        self,
        property_address_service: PropertyAddressService,
        property_matcher: PropertyMatcher,
        market_feature_service: MarketFeatureService,
        model_predictor: ModelPredictor,
    ) -> None:
        self.property_address_service = property_address_service
        self.property_matcher = property_matcher
        self.market_feature_service = market_feature_service
        self.model_predictor = model_predictor

    def _resolve(
        self,
        request: DiagnosisRequest,
    ) -> PropertyAddressResult:
        """주소·건축물대장 정보를 확보한다.

        properties/resolve 에서 받은 스냅샷이 그대로 돌아왔으면 재사용해
        도로명주소·건축물대장 API 재호출을 건너뛴다.
        스냅샷이 없거나 이번 요청과 대상이 다르거나 복원에 실패하면 다시 조회한다.
        """
        snapshot = request.property_snapshot

        if snapshot is not None:
            if matches_request(
                snapshot,
                request.address,
                request.dong_name,
                request.ho_name,
            ):
                try:
                    return restore_property_address_result(snapshot)
                except Exception:
                    logger.warning(
                        "매물 스냅샷 복원 실패, 주소를 다시 조회합니다",
                        exc_info=True,
                    )
            else:
                logger.info(
                    "매물 스냅샷이 요청과 달라 주소를 다시 조회합니다"
                )

        return self.property_address_service.resolve(
            address=request.address,
            dong_name=request.dong_name,
            ho_name=request.ho_name,
        )

    def analyze(
        self,
        request: DiagnosisRequest,
        land_right_area: Decimal | None = None,
    ) -> DiagnosisPipelineResult:
        resolved = self._resolve(request)

        if (
            resolved.housing_type != HousingType.DETACHED_MULTI
            and not request.ho_name
        ):
            raise ValueError("공동주택 호 정보 필요")

        if (
            resolved.housing_type == HousingType.DETACHED_MULTI
            and request.contract_area is None
        ):
            raise ValueError("단독·다가구 계약면적 필요")

        if (
            resolved.housing_type != HousingType.DETACHED_MULTI
            and request.exclusive_area is None
        ):
            raise ValueError("공동주택 전용면적 필요")

        model_type = MODEL_TYPES[resolved.housing_type]
        sale_key = f"매매_{model_type}"
        lease_key = f"전세_{model_type}"
        warnings = {
            *resolved.building_ledger.quality.blocking_errors,
            *resolved.building_ledger.quality.warnings,
        }
        matched_name = None

        if resolved.housing_type != HousingType.DETACHED_MULTI:
            matched = self.property_matcher.match(
                address=resolved.address,
                housing_type=resolved.housing_type,
                observed_building_name=(
                    resolved.building_ledger.selected_title.get("bldNm")
                ),
            )
            matched_name = matched.model_name
            warnings.update(matched.warnings)

        sale_input = PropertyFeatureFactory.create(
            result=resolved,
            model_key=sale_key,
            contract_date=request.contract_date,
            matched_name=matched_name,
            contract_area=request.contract_area,
            exclusive_area=request.exclusive_area,
            floor=request.floor,
            land_right_area=land_right_area,
        )
        lease_input = PropertyFeatureFactory.create(
            result=resolved,
            model_key=lease_key,
            contract_date=request.contract_date,
            matched_name=matched_name,
            contract_area=request.contract_area,
            exclusive_area=request.exclusive_area,
            floor=request.floor,
            land_right_area=land_right_area,
        )
        sale_market = self.market_feature_service.enrich(
            sale_key,
            sale_input,
        )
        lease_market = self.market_feature_service.enrich(
            lease_key,
            lease_input,
        )
        warnings.update(sale_market.warnings)
        warnings.update(lease_market.warnings)
        sale = self.model_predictor.predict(
            sale_key,
            sale_market.feature_input,
        )
        lease = self.model_predictor.predict(
            lease_key,
            lease_market.feature_input,
        )
        fallback_features = {
            *(f"매매:{name}" for name in sale.fallback_features),
            *(f"전세:{name}" for name in lease.fallback_features),
        }
        # 원천이 없어 늘 기본값을 쓰는 Feature는 신뢰도를 떨어뜨리는 대신
        # 경고로만 남긴다. (feature_sources.UNAVAILABLE_FEATURES 주석 참고)
        warnings.update(
            UNAVAILABLE_FEATURE_WARNINGS.get(
                name,
                "PROPERTY_FEATURE_UNAVAILABLE",
            )
            for name in (
                *sale.unavailable_features,
                *lease.unavailable_features,
            )
        )
        estimated_sale_price = round(sale.total_price)
        estimated_lease_price = round(lease.total_price)
        registry_risk = RegistryRiskAdapter.adapt(request.registry_risk)
        risk_indicators = RiskIndicatorCalculator.calculate(
            estimated_sale_price=estimated_sale_price,
            estimated_lease_price=estimated_lease_price,
            deposit=request.deposit,
            active_max_claim_amount=registry_risk.active_max_claim_amount,
            collateral_expected=request.mode == DiagnosisMode.DETAILED,
        )
        risk_severity = RiskSeverityFactory.create(
            sale_market=sale_market,
            lease_market=lease_market,
        )
        risk_score = RiskRule.score(
            risk_indicators,
            risk_severity.severity,
        )
        forced_warning = ForcedWarningRule.apply(
            risk_score.total,
            registry_risk.forced_warning_input,
            registry_required=request.mode == DiagnosisMode.DETAILED,
        )
        missing_checks = {
            *risk_indicators.missing_checks,
            *forced_warning.missing_checks,
        }

        return DiagnosisPipelineResult(
            normalized_address=resolved.address.road_address,
            housing_type=resolved.housing_type,
            sale=sale,
            lease=lease,
            estimated_sale_price=estimated_sale_price,
            estimated_lease_price=estimated_lease_price,
            risk_indicators=risk_indicators,
            risk_severity=risk_severity,
            risk_score=risk_score,
            forced_warning=forced_warning,
            warnings=tuple(sorted(warnings)),
            missing_checks=tuple(sorted(missing_checks)),
            fallback_features=tuple(sorted(fallback_features)),
        )
