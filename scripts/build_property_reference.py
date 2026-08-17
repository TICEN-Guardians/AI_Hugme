import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd
import pyarrow.parquet as parquet


MODEL_SPECS = {
    "매매_아파트": ("APARTMENT", "단지명"),
    "매매_연립다세대": ("VILLA", "건물명"),
    "매매_오피스텔": ("OFFICETEL", "단지명"),
    "전세_아파트": ("APARTMENT", "단지명"),
    "전세_연립다세대": ("VILLA", "건물명"),
    "전세_오피스텔": ("OFFICETEL", "단지명"),
}
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="6개 06 결합 parquet 디렉터리",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="MODEL_KEY=PATH",
        help="개별 원천 지정, 반복 가능",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""

    return " ".join(str(value).split())


def normalize_number(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    return text.zfill(4) if text.isdigit() else ""


def parse_sources(args: argparse.Namespace) -> dict[str, Path]:
    sources: dict[str, Path] = {}

    for value in args.source:
        model_key, separator, path = value.partition("=")

        if not separator or model_key not in MODEL_SPECS:
            raise ValueError(f"원천 형식 오류: {value}")

        sources[model_key] = Path(path)

    if args.source_dir:
        for model_key in MODEL_SPECS:
            matches = sorted(
                args.source_dir.glob(f"06_*{model_key}*.parquet")
            )

            if len(matches) == 1:
                sources.setdefault(model_key, matches[0])
            elif len(matches) > 1:
                raise ValueError(f"원천 파일 중복: {model_key}")

    if not sources:
        raise ValueError("Property Reference 원천 없음")

    missing = [
        model_key
        for model_key in MODEL_SPECS
        if model_key not in sources
    ]

    if missing:
        raise ValueError(f"원천 파일 누락: {missing}")

    for model_key, path in sources.items():
        if not path.is_file():
            raise FileNotFoundError(f"원천 파일 없음: {model_key}={path}")

    return sources


def read_source(model_key: str, path: Path) -> pd.DataFrame:
    housing_type, name_column = MODEL_SPECS[model_key]
    columns = {"시군구", "본번", "부번", name_column}
    schema_columns = set(parquet.ParquetFile(path).schema.names)

    if not columns.issubset(schema_columns):
        missing = sorted(columns - schema_columns)
        raise ValueError(f"{model_key} 필수 컬럼 누락: {missing}")

    data = pd.read_parquet(path, columns=sorted(columns))
    result = pd.DataFrame(
        {
            "district": data["시군구"].map(normalize_text),
            "bun": data["본번"].map(normalize_number),
            "ji": data["부번"].map(normalize_number),
            "housing_type": housing_type,
            "model_name": data[name_column].map(normalize_text),
            "source_building_name": "",
        }
    )
    valid = result[
        result["district"].ne("")
        & result["bun"].ne("")
        & result["ji"].ne("")
        & result["model_name"].ne("")
    ]
    grouped = (
        valid.groupby(list(result.columns), dropna=False)
        .size()
        .rename("sample_count")
        .reset_index()
    )
    print(
        f"- {model_key}: rows={len(data)}, "
        f"valid={len(valid)}, references={len(grouped)}"
    )
    return grouped


def write_database(
    output: Path,
    sources: dict[str, Path],
    references: pd.DataFrame,
) -> None:
    if output.exists():
        raise FileExistsError(f"출력 파일 이미 존재: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(output) as connection:
        connection.executescript(
            """
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE property_reference (
                district TEXT NOT NULL,
                bun TEXT NOT NULL,
                ji TEXT NOT NULL,
                housing_type TEXT NOT NULL,
                model_name TEXT NOT NULL,
                source_building_name TEXT NOT NULL,
                sample_count INTEGER NOT NULL CHECK (sample_count > 0),
                PRIMARY KEY (
                    district, bun, ji, housing_type,
                    model_name, source_building_name
                )
            );
            CREATE INDEX idx_property_reference_parcel
                ON property_reference (
                    district, bun, ji, housing_type
                );
            CREATE INDEX idx_property_reference_district
                ON property_reference (district, housing_type);
            CREATE INDEX idx_property_reference_type
                ON property_reference (housing_type);
            """
        )
        metadata = {
            "version": "property-reference-v2",
            "sources": json.dumps(
                {
                    key: path.name
                    for key, path in sorted(sources.items())
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        }
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            metadata.items(),
        )
        connection.executemany(
            """
            INSERT INTO property_reference (
                district, bun, ji, housing_type,
                model_name, source_building_name, sample_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (*row[:-1], int(row[-1]))
                for row in references.itertuples(
                    index=False,
                    name=None,
                )
            ),
        )


def main() -> None:
    args = parse_args()
    sources = parse_sources(args)
    frames = [
        read_source(model_key, path)
        for model_key, path in sorted(sources.items())
    ]
    references = (
        pd.concat(frames, ignore_index=True)
        .groupby(
            [
                "district",
                "bun",
                "ji",
                "housing_type",
                "model_name",
                "source_building_name",
            ],
            dropna=False,
        )["sample_count"]
        .sum()
        .reset_index()
    )
    write_database(args.output, sources, references)
    print(f"Property Reference 생성 완료: {args.output}")
    print(f"- references: {len(references)}")


if __name__ == "__main__":
    main()
