from pathlib import Path
from typing import Any

from app.diagnosis.feature_builder import ModelFeatures


class CatBoostAdapter:
    def __init__(self) -> None:
        self.model: Any = None

    def load(self, model_path: Path) -> None:
        from catboost import CatBoostRegressor

        model = CatBoostRegressor()
        model.load_model(str(model_path))

        self.model = model

    @property
    def feature_names(self) -> tuple[str, ...]:
        if self.model is None:
            raise RuntimeError("모델 로딩 전")

        return tuple(self.model.feature_names_)

    def predict(
        self,
        features: ModelFeatures,
    ) -> float:
        if self.model is None:
            raise RuntimeError("모델 로딩 전")

        from catboost import Pool

        pool = Pool(
            data=[features.as_row()],
            feature_names=list(features.names),
            cat_features=list(
                features.categorical_indices
            ),
        )

        prediction = self.model.predict(pool)

        return float(prediction[0])