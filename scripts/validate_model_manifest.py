import json

from app.diagnosis.feature_contract import (
    FEATURE_MANIFEST_VERSION,
    load_feature_contract,
)
from app.diagnosis.model.model_manifest import (
    load_model_manifest,
)


def main() -> None:
    contract = load_feature_contract()

    models = {
        model_key: {
            "framework": "catboost",
            "format": "cbm",
            "s3_key": (
                f"artifacts/{model_key}.cbm"
            ),
            "sha256": "0" * 64,
        }
        for model_key in contract.models
    }

    content = json.dumps(
        {
            "version": "test-v1",
            "feature_manifest_version": (
                FEATURE_MANIFEST_VERSION
            ),
            "models": models,
        },
        ensure_ascii=False,
    )

    manifest = load_model_manifest(
        content=content,
        expected_model_keys=set(contract.models),
        expected_feature_version=(
            FEATURE_MANIFEST_VERSION
        ),
    )

    assert len(manifest.models) == 8

    print(
        "Model Manifest 검증 완료: "
        f"version={manifest.version}, "
        f"models={len(manifest.models)}"
    )


if __name__ == "__main__":
    main()