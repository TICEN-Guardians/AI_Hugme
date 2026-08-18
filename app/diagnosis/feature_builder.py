from dataclasses import dataclass

from app.diagnosis.feature_contract import FeatureContract
from app.diagnosis.feature_fallback import FeatureFallbackPolicy
from app.diagnosis.feature_input import FeatureInput, FeatureValue
from app.diagnosis.feature_sources import FeatureSource


@dataclass(frozen=True)
class ModelFeatures:
    model_key: str
    names: tuple[str, ...]
    values: tuple[FeatureValue, ...]
    categorical_indices: tuple[int, ...]
    fallback_features: tuple[str, ...] = ()

    def as_row(self) -> list[FeatureValue]:
        return list(self.values)


class FeatureBuilder:
    def __init__(
        self,
        contract: FeatureContract,
        fallback_policy: FeatureFallbackPolicy | None = None,
    ) -> None:
        self.contract = contract
        self.fallback_policy = fallback_policy

    def build(
        self,
        model_key: str,
        feature_input: FeatureInput,
    ) -> ModelFeatures:
        model = self.contract.get_model(model_key)
        available: dict[str, FeatureValue] = {}

        for source in FeatureSource:
            available.update(
                feature_input.values_for(source)
            )

        available.update(
            self._derived_values(feature_input)
        )

        values = []
        fallback_features = []

        for name in model.features:
            value = available.get(name)

            if self.fallback_policy:
                value, fallback_used = (
                    self.fallback_policy.resolve(
                        model_key=model_key,
                        feature_name=name,
                        value=value,
                        categorical=(
                            name in model.categorical_features
                        ),
                    )
                )

                if fallback_used:
                    fallback_features.append(name)
            elif value is None:
                raise ValueError(
                    f"{model_key} Feature 누락: {name}"
                )

            values.append(value)

        categorical_indices = tuple(
            index
            for index, name in enumerate(model.features)
            if name in model.categorical_features
        )

        return ModelFeatures(
            model_key=model_key,
            names=model.features,
            values=tuple(values),
            categorical_indices=categorical_indices,
            fallback_features=tuple(fallback_features),
        )

    @staticmethod
    def _derived_values(
        feature_input: FeatureInput,
    ) -> dict[str, FeatureValue]:
        building = feature_input.building_ledger

        approval_year = building.get("사용승인연도")
        gross_area = building.get("연면적(㎡)")
        land_area = building.get("대지면적(㎡)")

        building_age = None

        if isinstance(approval_year, int):
            building_age = (
                feature_input.contract_date.year
                - approval_year
            )

        area_ratio = None

        if (
            isinstance(gross_area, (int, float))
            and isinstance(land_area, (int, float))
            and land_area != 0
        ):
            area_ratio = gross_area / land_area

        return {
            "계약월": feature_input.contract_date.month,
            "계약월_파생": feature_input.contract_date.month,
            "최종건축연령": building_age,
            "거래시점건축연령_파생": building_age,
            "대지대비연면적비율_파생": area_ratio,
        }
