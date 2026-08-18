import json
import math
from dataclasses import dataclass

from app.diagnosis.feature_input import FeatureValue
from app.diagnosis.feature_contract import (
    FEATURE_MANIFEST_VERSION,
    FeatureContract,
)


@dataclass(frozen=True)
class FeatureFallbackPolicy:
    defaults: dict[str, dict[str, FeatureValue]]

    def resolve(
        self,
        model_key: str,
        feature_name: str,
        value: FeatureValue,
        categorical: bool,
    ) -> tuple[FeatureValue, bool]:
        if self._valid(value, categorical):
            return value, False

        default = self.defaults.get(
            model_key,
            {},
        ).get(feature_name)

        if not self._valid(default, categorical):
            raise ValueError(
                f"{model_key} fallback 없음: "
                f"{feature_name}"
            )

        return default, True

    @staticmethod
    def _valid(
        value: FeatureValue,
        categorical: bool,
    ) -> bool:
        if categorical:
            return bool(str(value or "").strip())

        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )


def load_feature_fallback_policy(
    content: str,
    contract: FeatureContract,
) -> FeatureFallbackPolicy:
    data = json.loads(content)
    defaults = data["models"]

    if not data.get("version"):
        raise ValueError("Fallback 버전 없음")

    if (
        data.get("feature_manifest_version")
        != FEATURE_MANIFEST_VERSION
    ):
        raise ValueError("Fallback Feature 버전 불일치")

    if set(defaults) != set(contract.models):
        raise ValueError("Fallback 모델 키 불일치")

    policy = FeatureFallbackPolicy(defaults)

    for model_key, model in contract.models.items():
        if set(defaults[model_key]) != set(model.features):
            raise ValueError(
                f"{model_key} Fallback Feature 불일치"
            )

        for name in model.features:
            policy.resolve(
                model_key=model_key,
                feature_name=name,
                value=None,
                categorical=(
                    name in model.categorical_features
                ),
            )

        area_name = model.target["area_feature"]

        if area_name and defaults[model_key][area_name] <= 0:
            raise ValueError(
                f"{model_key} 면적 Fallback 오류"
            )

    return policy
