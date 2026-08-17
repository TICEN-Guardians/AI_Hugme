import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd


FEATURE_NAMES = {
    ("가격지수", "원자료"): "RONE_가격지수",
    ("가격지수", "전기대비증감률"): "RONE_가격지수_전월비",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def feature_name(row: pd.Series) -> str | None:
    key = (row["지표분류"], row["세부지표"])

    if key in FEATURE_NAMES:
        return FEATURE_NAMES[key]

    if row["지표분류"] == "중위단위가격":
        return "RONE_중위단위가격_천원㎡"

    if (
        row["지표분류"] == "오피스텔가격"
        and "평균단위당" in row["세부지표"]
    ):
        return "RONE_평균단위가격_천원㎡"

    return None


def load_values(source: Path) -> pd.DataFrame:
    columns = [
        "거래유형",
        "주택유형",
        "지표분류",
        "지역경로",
        "최종지역명",
        "규모",
        "기준연월",
        "세부지표",
        "수치값",
        "값상태",
    ]
    data = pd.read_csv(
        source,
        usecols=columns,
        encoding="utf-8-sig",
    )
    data = data[data["값상태"].eq("정상")].copy()
    data["feature_name"] = data.apply(feature_name, axis=1)
    data = data[data["feature_name"].notna()].copy()
    data["value"] = pd.to_numeric(data["수치값"], errors="coerce")
    data = data[data["value"].notna()].copy()
    result = data.rename(
        columns={
            "거래유형": "transaction_type",
            "주택유형": "housing_type",
            "지역경로": "region_path",
            "최종지역명": "region_name",
            "규모": "size_band",
            "기준연월": "base_month",
        }
    )[
        [
            "transaction_type",
            "housing_type",
            "region_path",
            "region_name",
            "size_band",
            "base_month",
            "feature_name",
            "value",
        ]
    ]
    duplicates = result.duplicated(result.columns[:-1], keep=False)

    if duplicates.any():
        raise ValueError(f"RONE 중복 키: {int(duplicates.sum())}")

    return result


def write_database(
    source: Path,
    output: Path,
    values: pd.DataFrame,
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
            CREATE TABLE rone_value (
                transaction_type TEXT NOT NULL,
                housing_type TEXT NOT NULL,
                region_path TEXT NOT NULL,
                region_name TEXT NOT NULL,
                size_band TEXT NOT NULL,
                base_month TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (
                    transaction_type, housing_type,
                    region_path, size_band,
                    base_month, feature_name
                )
            );
            CREATE INDEX idx_rone_lookup
                ON rone_value (
                    transaction_type, housing_type,
                    size_band, feature_name, base_month
                );
            CREATE INDEX idx_rone_region
                ON rone_value (region_name, region_path);
            """
        )
        metadata = {
            "version": "rone-v1",
            "source": source.name,
            "rows": str(len(values)),
        }
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            metadata.items(),
        )
        connection.executemany(
            "INSERT INTO rone_value VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            values.itertuples(index=False, name=None),
        )


def main() -> None:
    args = parse_args()

    if not args.source.is_file():
        raise FileNotFoundError(f"RONE 원천 없음: {args.source}")

    values = load_values(args.source)
    write_database(args.source, args.output, values)
    summary = (
        values.groupby(["transaction_type", "housing_type"])
        .size()
        .to_dict()
    )
    print(f"RONE Store 생성 완료: {args.output}")
    print(f"- rows: {len(values)}")
    print(json.dumps(
        {" / ".join(key): int(value) for key, value in summary.items()},
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
