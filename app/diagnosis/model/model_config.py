import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    region: str
    bucket: str
    manifest_key: str
    cache_dir: Path


def load_model_config() -> ModelConfig:
    bucket = os.getenv("MODEL_S3_BUCKET", "")
    manifest_key = os.getenv(
        "MODEL_MANIFEST_KEY",
        "",
    )

    if not bucket:
        raise ValueError("MODEL_S3_BUCKET 없음")

    if not manifest_key:
        raise ValueError("MODEL_MANIFEST_KEY 없음")

    return ModelConfig(
        region=os.getenv(
            "AWS_REGION",
            "ap-northeast-2",
        ),
        bucket=bucket,
        manifest_key=manifest_key,
        cache_dir=Path(
            os.getenv(
                "MODEL_CACHE_DIR",
                ".cache/models",
            )
        ),
    )