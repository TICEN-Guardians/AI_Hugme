import math
from dataclasses import dataclass

from app.diagnosis.feature_builder import ModelFeatures
from app.diagnosis.feature_contract import FeatureContract


@dataclass(frozen=True)
class PredictionResult:
    model_key: str
    raw_prediction: float
    unit_price: float | None
    total_price: float
    fallback_features: tuple[str, ...] = ()
    unavailable_features: tuple[str, ...] = ()


class TargetTransformer:
    def __init__(
        self,
        contract: FeatureContract,
    ) -> None:
        self.contract = contract

    def transform(
        self,
        model_key: str,
        raw_prediction: float,
        features: ModelFeatures,
    ) -> PredictionResult:
        if features.model_key != model_key:
            raise ValueError("모델 키 불일치")

        if not math.isfinite(raw_prediction):
            raise ValueError("예측값 오류")

        model = self.contract.get_model(model_key)
        target = model.target

        if target["inverse_primary"] != "exp(y_pred)":
            raise ValueError(
                "지원하지 않는 Target 역변환"
            )

        primary_value = math.exp(raw_prediction)
        area_feature = target["area_feature"]

        if not area_feature:
            return PredictionResult(
                model_key=model_key,
                raw_prediction=raw_prediction,
                unit_price=None,
                total_price=primary_value,
                fallback_features=features.fallback_features,
                unavailable_features=features.unavailable_features,
            )

        area = self._get_area(
            feature_name=area_feature,
            features=features,
        )

        return PredictionResult(
            model_key=model_key,
            raw_prediction=raw_prediction,
            unit_price=primary_value,
            total_price=primary_value * area,
            fallback_features=features.fallback_features,
            unavailable_features=features.unavailable_features,
        )

    @staticmethod
    def _get_area(
        feature_name: str,
        features: ModelFeatures,
    ) -> float:
        try:
            index = features.names.index(feature_name)
        except ValueError as error:
            raise ValueError(
                f"면적 Feature 없음: {feature_name}"
            ) from error

        area = features.values[index]

        if (
            not isinstance(area, (int, float))
            or isinstance(area, bool)
            or area <= 0
        ):
            raise ValueError(
                f"면적값 오류: {feature_name}"
            )

        return float(area)
