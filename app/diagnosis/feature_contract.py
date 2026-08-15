import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODEL_COUNT = 8
TOTAL_FEATURE_COUNT = 140

MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "artifacts"
    / "contracts"
    / "model_feature_manifest_v2_active_140.json"
)


@dataclass(frozen=True)
class ModelFeatureContract:
    model_key: str
    feature_count: int
    features: tuple[str, ...]
    categorical_features: tuple[str, ...]
    inactive_features: tuple[str, ...]
    target: dict[str, str]


@dataclass(frozen=True)
class FeatureContract:
    models: dict[str, ModelFeatureContract]

    @property
    def model_count(self) -> int:
        return len(self.models)

    @property
    def total_feature_count(self) -> int:
        return sum(
            model.feature_count
            for model in self.models.values()
        )

    def get_model(
        self,
        model_key: str,
    ) -> ModelFeatureContract:
        if model_key not in self.models:
            raise ValueError(
                f"등록되지 않은 모델 계약: {model_key}"
            )

        return self.models[model_key]


def load_feature_contract(
    manifest_path: Path = MANIFEST_PATH,
) -> FeatureContract:
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Feature Manifest 없음: {manifest_path}"
        )

    with manifest_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        manifest: dict[str, Any] = json.load(file)

    models = {
        model_key: ModelFeatureContract(
            model_key=model_key,
            feature_count=data["feature_count"],
            features=tuple(data["features"]),
            categorical_features=tuple(
                data["categorical_features"]
            ),
            inactive_features=tuple(
                data["inactive_features"]
            ),
            target=data["target"],
        )
        for model_key, data in manifest.items()
    }

    contract = FeatureContract(models=models)
    _validate_contract(contract)

    return contract


def _validate_contract(
    contract: FeatureContract,
) -> None:
    if contract.model_count != MODEL_COUNT:
        raise ValueError(
            f"모델 개수 불일치: {contract.model_count}"
        )

    if contract.total_feature_count != TOTAL_FEATURE_COUNT:
        raise ValueError(
            "전체 Feature 개수 불일치: "
            f"{contract.total_feature_count}"
        )

    for model in contract.models.values():
        if model.feature_count != len(model.features):
            raise ValueError(
                f"{model.model_key} Feature 개수 불일치"
            )

        if len(model.features) != len(set(model.features)):
            raise ValueError(
                f"{model.model_key} Feature 중복"
            )

        unknown_categories = (
            set(model.categorical_features)
            - set(model.features)
        )

        if unknown_categories:
            raise ValueError(
                f"{model.model_key} 범주형 Feature 오류: "
                f"{sorted(unknown_categories)}"
            )

        active_inactive_duplicates = (
            set(model.features)
            & set(model.inactive_features)
        )

        if active_inactive_duplicates:
            raise ValueError(
                f"{model.model_key} 활성·비활성 Feature 중복"
            )