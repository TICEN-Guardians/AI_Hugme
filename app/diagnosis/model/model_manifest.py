import json
from dataclasses import dataclass
from string import hexdigits
from typing import Any


@dataclass(frozen=True)
class ModelArtifact:
    s3_key: str
    sha256: str


@dataclass(frozen=True)
class ModelManifest:
    version: str
    feature_manifest_version: str
    models: dict[str, ModelArtifact]


def load_model_manifest(
    content: str,
    expected_model_keys: set[str],
    expected_feature_version: str,
) -> ModelManifest:
    data: dict[str, Any] = json.loads(content)

    models = {
        model_key: ModelArtifact(
            s3_key=value["s3_key"],
            sha256=value["sha256"].lower(),
        )
        for model_key, value in data["models"].items()
    }

    manifest = ModelManifest(
        version=data["version"],
        feature_manifest_version=(
            data["feature_manifest_version"]
        ),
        models=models,
    )

    _validate_manifest(
        manifest=manifest,
        expected_model_keys=expected_model_keys,
        expected_feature_version=(
            expected_feature_version
        ),
    )

    return manifest


def _validate_manifest(
    manifest: ModelManifest,
    expected_model_keys: set[str],
    expected_feature_version: str,
) -> None:
    if not manifest.version:
        raise ValueError("모델 버전 없음")

    if (
        manifest.feature_manifest_version
        != expected_feature_version
    ):
        raise ValueError(
            "Feature Manifest 버전 불일치"
        )

    if set(manifest.models) != expected_model_keys:
        raise ValueError(
            "모델 키 불일치"
        )

    s3_keys = [
        artifact.s3_key
        for artifact in manifest.models.values()
    ]

    if len(s3_keys) != len(set(s3_keys)):
        raise ValueError("S3 모델 경로 중복")

    for model_key, artifact in manifest.models.items():
        if not artifact.s3_key.endswith(".cbm"):
            raise ValueError(
                f"{model_key} 모델 확장자 오류"
            )

        if (
            len(artifact.sha256) != 64
            or any(
                char not in hexdigits
                for char in artifact.sha256
            )
        ):
            raise ValueError(
                f"{model_key} SHA-256 오류"
            )