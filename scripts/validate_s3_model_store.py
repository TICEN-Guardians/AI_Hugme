import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.diagnosis.feature_contract import (
    FEATURE_MANIFEST_VERSION,
    load_feature_contract,
)
from app.diagnosis.model.model_config import ModelConfig
from app.diagnosis.model.s3_model_store import S3ModelStore


MODEL_CONTENT = b"test-model"


class FakeS3:
    def __init__(self, manifest: str) -> None:
        self.manifest = manifest

    def get_object(
        self,
        Bucket: str,
        Key: str,
    ) -> dict:
        return {
            "Body": io.BytesIO(
                self.manifest.encode("utf-8")
            )
        }

    def download_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> None:
        Path(file_path).write_bytes(MODEL_CONTENT)


def main() -> None:
    contract = load_feature_contract()
    checksum = hashlib.sha256(
        MODEL_CONTENT
    ).hexdigest()

    models = {
        model_key: {
            "s3_key": f"artifacts/{model_key}.cbm",
            "sha256": checksum,
        }
        for model_key in contract.models
    }

    manifest_content = json.dumps(
        {
            "version": "test-v1",
            "feature_manifest_version": (
                FEATURE_MANIFEST_VERSION
            ),
            "models": models,
        },
        ensure_ascii=False,
    )

    with TemporaryDirectory() as temp_dir:
        config = ModelConfig(
            region="ap-northeast-2",
            bucket="test-bucket",
            manifest_key="model-manifest.json",
            cache_dir=Path(temp_dir),
        )

        store = S3ModelStore(
            config=config,
            s3_client=FakeS3(manifest_content),
        )

        manifest = store.load_manifest(
            set(contract.models)
        )

        model_key = next(iter(contract.models))
        model_path = store.get_model_path(
            manifest=manifest,
            model_key=model_key,
        )

        assert model_path.read_bytes() == MODEL_CONTENT

    print("S3ModelStore 검증 완료")


if __name__ == "__main__":
    main()