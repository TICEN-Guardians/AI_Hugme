from pathlib import Path

from app.diagnosis.feature_contract import (
    load_feature_contract,
)
from app.diagnosis.model.model_manifest import (
    ModelArtifact,
    ModelManifest,
)
from app.diagnosis.model.model_registry import (
    ModelRegistry,
)


class FakeStore:
    def __init__(self) -> None:
        self.download_count = 0

    def load_manifest(
        self,
        expected_model_keys: set[str],
    ) -> ModelManifest:
        models = {
            key: ModelArtifact(
                framework="fake",
                format="test",
                s3_key=f"{key}.test",
                sha256="0" * 64,
            )
            for key in expected_model_keys
        }

        return ModelManifest(
            version="test-v1",
            feature_manifest_version=(
                "ModelFeatureManifest_v2"
            ),
            models=models,
        )

    def get_model_path(
        self,
        manifest: ModelManifest,
        model_key: str,
    ) -> Path:
        self.download_count += 1
        return Path(model_key)


class FakeAdapter:
    def __init__(self, contract) -> None:
        self.contract = contract
        self.model_key = ""

    def load(self, model_path: Path) -> None:
        self.model_key = model_path.name

    @property
    def feature_names(self) -> tuple[str, ...]:
        return self.contract.get_model(
            self.model_key
        ).features

    def predict(self, features) -> float:
        return 1.0


def main() -> None:
    contract = load_feature_contract()
    store = FakeStore()

    registry = ModelRegistry(
        contract=contract,
        model_store=store,
        adapter_factories={
            "fake": lambda: FakeAdapter(contract),
        },
    )

    first = registry.get("전세_아파트")
    second = registry.get("전세_아파트")

    assert first is second
    assert store.download_count == 1
    assert registry.loaded_model_count == 1

    print("ModelRegistry 검증 완료")


if __name__ == "__main__":
    main()