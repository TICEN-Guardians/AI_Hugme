import math

from app.diagnosis.feature_builder import ModelFeatures
from app.diagnosis.feature_contract import (
    load_feature_contract,
)
from app.diagnosis.model.model_predictor import (
    ModelPredictor,
)
from app.diagnosis.model.target_transform import (
    TargetTransformer,
)


class FakeBuilder:
    def __init__(self, contract) -> None:
        self.contract = contract

    def build(
        self,
        model_key: str,
        feature_input,
    ) -> ModelFeatures:
        model = self.contract.get_model(model_key)
        values = [1.0] * model.feature_count
        area_feature = model.target["area_feature"]

        if area_feature:
            area_index = model.features.index(
                area_feature
            )
            values[area_index] = 10.0

        return ModelFeatures(
            model_key=model_key,
            names=model.features,
            values=tuple(values),
            categorical_indices=(),
        )


class FakeAdapter:
    def predict(
        self,
        features: ModelFeatures,
    ) -> float:
        return math.log(1000.0)


class FakeRegistry:
    def get(self, model_key: str) -> FakeAdapter:
        return FakeAdapter()


def main() -> None:
    contract = load_feature_contract()

    predictor = ModelPredictor(
        feature_builder=FakeBuilder(contract),
        model_registry=FakeRegistry(),
        target_transformer=TargetTransformer(
            contract
        ),
    )

    for model in contract.models.values():
        result = predictor.predict(
            model_key=model.model_key,
            feature_input=None,
        )

        expected_total = (
            10000.0
            if model.target["area_feature"]
            else 1000.0
        )

        assert math.isclose(
            result.total_price,
            expected_total,
        )

        print(
            f"- {model.model_key}: "
            f"total={result.total_price}"
        )

    print("ModelPredictor 검증 완료")


if __name__ == "__main__":
    main()