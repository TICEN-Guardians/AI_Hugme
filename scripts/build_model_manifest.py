import argparse
import hashlib
import json
from pathlib import Path

from app.diagnosis.feature_contract import (
    FEATURE_MANIFEST_VERSION,
    load_feature_contract,
)
from app.diagnosis.model.model_manifest import (
    load_model_manifest,
)


def calculate_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def find_model_file(
    model_dir: Path,
    model_key: str,
    extension: str,
) -> Path:
    matches = [
        file_path
        for file_path in model_dir.glob(
            f"*.{extension}"
        )
        if model_key in file_path.stem
    ]

    if len(matches) != 1:
        raise ValueError(
            f"{model_key} 모델 파일 개수: "
            f"{len(matches)}"
        )

    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-dir",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--version",
        required=True,
    )
    parser.add_argument(
        "--s3-prefix",
        required=True,
    )
    parser.add_argument(
        "--framework",
        required=True,
    )
    parser.add_argument(
        "--format",
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    args = parser.parse_args()
    file_format = args.format.lstrip(".")

    contract = load_feature_contract()
    models = {}

    for model_key in contract.models:
        model_file = find_model_file(
            model_dir=args.model_dir,
            model_key=model_key,
            extension=file_format,
        )

        models[model_key] = {
            "framework": args.framework,
            "format": file_format,
            "s3_key": (
                f"{args.s3_prefix.rstrip('/')}/"
                f"{model_file.name}"
            ),
            "sha256": calculate_sha256(model_file),
        }

        print(f"- {model_key}: {model_file.name}")

    manifest_data = {
        "version": args.version,
        "feature_manifest_version": (
            FEATURE_MANIFEST_VERSION
        ),
        "models": models,
    }

    content = json.dumps(
        manifest_data,
        ensure_ascii=False,
        indent=2,
    )

    load_model_manifest(
        content=content,
        expected_model_keys=set(contract.models),
        expected_feature_version=(
            FEATURE_MANIFEST_VERSION
        ),
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.output.write_text(
        content,
        encoding="utf-8",
    )

    print(f"Manifest 생성 완료: {args.output}")


if __name__ == "__main__":
    main()