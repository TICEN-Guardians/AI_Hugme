import hashlib
from pathlib import Path
from typing import Any

import boto3

from app.diagnosis.feature_contract import (
    FEATURE_MANIFEST_VERSION,
)
from app.diagnosis.model.model_config import ModelConfig
from app.diagnosis.model.model_manifest import (
    ModelManifest,
    load_model_manifest,
)


class S3ModelStore:
    def __init__(
        self,
        config: ModelConfig,
        s3_client: Any = None,
    ) -> None:
        self.config = config
        self.s3 = s3_client or boto3.client(
            "s3",
            region_name=config.region,
        )

    def load_manifest(
        self,
        expected_model_keys: set[str],
    ) -> ModelManifest:
        response = self.s3.get_object(
            Bucket=self.config.bucket,
            Key=self.config.manifest_key,
        )

        content = response["Body"].read().decode(
            "utf-8"
        )

        return load_model_manifest(
            content=content,
            expected_model_keys=expected_model_keys,
            expected_feature_version=(
                FEATURE_MANIFEST_VERSION
            ),
        )

    def get_model_path(
        self,
        manifest: ModelManifest,
        model_key: str,
    ) -> Path:
        if model_key not in manifest.models:
            raise ValueError(
                f"등록되지 않은 모델: {model_key}"
            )

        artifact = manifest.models[model_key]
        file_name = Path(artifact.s3_key).name

        model_path = (
            self.config.cache_dir
            / manifest.version
            / file_name
        )

        if (
            model_path.is_file()
            and self._sha256(model_path)
            == artifact.sha256
        ):
            return model_path

        model_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = model_path.with_suffix(
            f"{model_path.suffix}.part"
        )

        try:
            self.s3.download_file(
                self.config.bucket,
                artifact.s3_key,
                str(temp_path),
            )

            if self._sha256(temp_path) != artifact.sha256:
                raise ValueError(
                    f"{model_key} SHA-256 불일치"
                )

            temp_path.replace(model_path)

        finally:
            if temp_path.exists():
                temp_path.unlink()

        return model_path

    @staticmethod
    def _sha256(file_path: Path) -> str:
        digest = hashlib.sha256()

        with file_path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)

        return digest.hexdigest()