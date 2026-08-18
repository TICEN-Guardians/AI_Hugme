import argparse
import gc
import math
from datetime import date
from pathlib import Path

from app.diagnosis.feature_builder import FeatureBuilder
from app.diagnosis.feature_contract import load_feature_contract
from app.diagnosis.feature_fallback import (
    load_feature_fallback_policy,
)
from app.diagnosis.feature_input import FeatureInput
from app.diagnosis.model.catboost_adapter import CatBoostAdapter
from app.diagnosis.model.target_transform import TargetTransformer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument(
        "--defaults",
        type=Path,
        default=Path("artifacts/contracts/feature-defaults.json"),
    )
    args = parser.parse_args()

    contract = load_feature_contract()
    policy = load_feature_fallback_policy(
        args.defaults.read_text(encoding="utf-8"),
        contract,
    )
    builder = FeatureBuilder(contract, policy)
    transformer = TargetTransformer(contract)
    feature_input = FeatureInput(
        contract_date=date(2026, 8, 16),
        normalized_address="fallback 검증",
        district="",
        housing_type="",
    )

    for model_key in contract.models:
        model_path = (
            args.model_dir
            / f"catboost_baseline_{model_key}.cbm"
        )
        features = builder.build(model_key, feature_input)
        adapter = CatBoostAdapter()
        adapter.load(model_path)
        raw_prediction = adapter.predict(features)
        result = transformer.transform(
            model_key,
            raw_prediction,
            features,
        )

        if not math.isfinite(result.total_price):
            raise ValueError(f"{model_key} 예측값 오류")

        if result.total_price <= 0:
            raise ValueError(f"{model_key} 예측값 음수 또는 0")

        print(
            f"- {model_key}: "
            f"fallback={len(result.fallback_features)}, "
            f"total={round(result.total_price)}"
        )

        del adapter
        gc.collect()

    print("Fallback 실제 모델 추론 검증 완료")


if __name__ == "__main__":
    main()
