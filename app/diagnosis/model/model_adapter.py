from pathlib import Path
from typing import Protocol

from app.diagnosis.feature_builder import ModelFeatures


class ModelAdapter(Protocol):
    def load(self, model_path: Path) -> None:
        ...

    @property
    def feature_names(self) -> tuple[str, ...]:
        ...

    def predict(
        self,
        features: ModelFeatures,
    ) -> float:
        ...