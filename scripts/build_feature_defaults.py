import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.diagnosis.feature_contract import (
    FEATURE_MANIFEST_VERSION,
    load_feature_contract,
)
from app.diagnosis.feature_fallback import (
    load_feature_fallback_policy,
)


def numeric_default(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce")
    values = values.replace([np.inf, -np.inf], np.nan).dropna()

    if values.empty:
        raise ValueError(f"숫자형 기본값 없음: {series.name}")

    return float(values.median())


def categorical_default(series: pd.Series) -> str:
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]

    if values.empty:
        raise ValueError(f"범주형 기본값 없음: {series.name}")

    counts = values.value_counts()
    maximum = int(counts.max())

    return sorted(
        str(value)
        for value, count in counts.items()
        if count == maximum
    )[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = load_feature_contract()
    models = {}

    for model_key, model in contract.models.items():
        path = args.train_dir / f"train_{model_key}.parquet"
        data = pd.read_parquet(
            path,
            columns=list(model.features),
        )
        categorical = set(model.categorical_features)
        models[model_key] = {
            name: (
                categorical_default(data[name])
                if name in categorical
                else numeric_default(data[name])
            )
            for name in model.features
        }

        print(f"- {model_key}: rows={len(data)}")

    payload = {
        "version": "train-v1",
        "feature_manifest_version": FEATURE_MANIFEST_VERSION,
        "models": models,
    }
    content = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )
    load_feature_fallback_policy(content, contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Feature 기본값 생성 완료: {args.output}")


if __name__ == "__main__":
    main()
