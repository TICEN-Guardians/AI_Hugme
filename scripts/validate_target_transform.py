import math

from app.diagnosis.feature_builder import ModelFeatures
from app.diagnosis.feature_contract import (
    load_feature_contract,
)
from app.diagnosis.model.target_transform import (
    TargetTransformer,
)


def main() -> None:
    contract = load_feature_contract()
    transformer = TargetTransformer(contract)

    for model in contract.models.values():
        values = [1.0] * model.feature_count
        area_feature = model.target["area_feature"]

        if area_feature:
            area_index = model.features.index(
                area_feature
            )
            values[area_index] = 10.0

        features = ModelFeatures(
            model_key=model.model_key,
            names=model.features,
            values=tuple(values),
            categorical_indices=(),
        )

        result = transformer.transform(
            model_key=model.model_key,
            raw_prediction=math.log(1000.0),
            features=features,
        )

        if area_feature:
            assert math.isclose(
                result.unit_price,
                1000.0,
            )
            assert math.isclose(
                result.total_price,
                10000.0,
            )
        else:
            assert result.unit_price is None
            assert math.isclose(
                result.total_price,
                1000.0,
            )

        print(
            f"- {model.model_key}: "
            f"total={result.total_price}"
        )

    print("Target 역변환 검증 완료")


if __name__ == "__main__":
    main()