from app.diagnosis.feature_builder import FeatureBuilder
from app.diagnosis.feature_input import FeatureInput
from app.diagnosis.model.model_registry import ModelRegistry
from app.diagnosis.model.target_transform import (
    PredictionResult,
    TargetTransformer,
)


class ModelPredictor:
    def __init__(
        self,
        feature_builder: FeatureBuilder,
        model_registry: ModelRegistry,
        target_transformer: TargetTransformer,
    ) -> None:
        self.feature_builder = feature_builder
        self.model_registry = model_registry
        self.target_transformer = target_transformer

    def predict(
        self,
        model_key: str,
        feature_input: FeatureInput,
    ) -> PredictionResult:
        features = self.feature_builder.build(
            model_key=model_key,
            feature_input=feature_input,
        )

        model = self.model_registry.get(model_key)
        raw_prediction = model.predict(features)

        return self.target_transformer.transform(
            model_key=model_key,
            raw_prediction=raw_prediction,
            features=features,
        )