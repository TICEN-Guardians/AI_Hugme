import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from app.diagnosis.feature_contract import load_feature_contract
from app.diagnosis.model.catboost_adapter import CatBoostAdapter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model-file", type=Path, required=True)
    args = parser.parse_args()

    contract = load_feature_contract().get_model(args.model_key)
    data = pd.read_parquet(args.dataset)
    missing = [name for name in contract.features if name not in data]

    if missing:
        raise ValueError(f"학습 데이터 Feature 누락: {missing}")

    active = data.loc[:, list(contract.features)]
    nulls = active.isna().sum()
    nulls = nulls[nulls > 0].to_dict()

    if nulls:
        raise ValueError(f"학습 데이터 결측: {nulls}")

    numeric_names = [
        name
        for name in contract.features
        if name not in contract.categorical_features
    ]
    try:
        numeric = active[numeric_names].apply(
            pd.to_numeric,
            errors="raise",
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "숫자형 Feature 변환 오류"
        ) from exc

    values = numeric.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError("숫자형 Feature NaN 또는 Inf")

    adapter = CatBoostAdapter()
    adapter.load(args.model_file)

    if adapter.feature_names != contract.features:
        raise ValueError("모델 Feature 이름·순서 불일치")

    print(f"학습 parity 검증 완료: {args.model_key}")
    print(f"- rows: {len(data)}")
    print(f"- active features: {len(contract.features)}")
    print(f"- categorical: {len(contract.categorical_features)}")
    print("- dataset/model/contract 일치")


if __name__ == "__main__":
    main()
