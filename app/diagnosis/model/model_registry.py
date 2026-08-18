from threading import Lock
from typing import Callable

from app.diagnosis.feature_contract import FeatureContract
from app.diagnosis.model.model_adapter import ModelAdapter
from app.diagnosis.model.s3_model_store import S3ModelStore


AdapterFactory = Callable[[], ModelAdapter]


class ModelRegistry:
    def __init__(
        self,
        contract: FeatureContract,
        model_store: S3ModelStore,
        adapter_factories: dict[
            str,
            AdapterFactory,
        ],
    ) -> None:
        self.contract = contract
        self.model_store = model_store
        self.adapter_factories = adapter_factories
        self.models: dict[str, ModelAdapter] = {}
        self.lock = Lock()

        self.manifest = model_store.load_manifest(
            set(contract.models)
        )

    def get(self, model_key: str) -> ModelAdapter:
        if model_key in self.models:
            return self.models[model_key]

        with self.lock:
            if model_key in self.models:
                return self.models[model_key]

            model = self._load(model_key)
            self.models[model_key] = model

            return model

    def _load(
        self,
        model_key: str,
    ) -> ModelAdapter:
        contract = self.contract.get_model(model_key)
        artifact = self.manifest.models[model_key]

        factory = self.adapter_factories.get(
            artifact.framework
        )

        if factory is None:
            raise ValueError(
                "지원하지 않는 모델 framework: "
                f"{artifact.framework}"
            )

        model_path = self.model_store.get_model_path(
            manifest=self.manifest,
            model_key=model_key,
        )

        model = factory()
        model.load(model_path)

        if model.feature_names != contract.features:
            raise ValueError(
                f"{model_key} Feature 계약 불일치"
            )

        return model

    @property
    def loaded_model_count(self) -> int:
        return len(self.models)