import argparse
import sqlite3
from pathlib import Path

import pandas as pd


FEATURE_COLUMNS = {
    "선행지수_순환변동치": "KOSIS_선행지수_순환변동치",
    "경제심리지수": "KOSIS_경제심리지수",
    "건설기성액": "KOSIS_건설기성액",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_values(source: Path) -> pd.DataFrame:
    columns = [
        "계약연월",
        "원자료_기준연월",
        "잠정치포함여부",
        "KOSIS_가용여부",
        "결합시차개월",
        *FEATURE_COLUMNS,
    ]
    data = pd.read_csv(source, usecols=columns, encoding="utf-8-sig")
    data = data[data["KOSIS_가용여부"].eq("Y")].copy()

    if not data["결합시차개월"].eq(2).all():
        raise ValueError("KOSIS 결합시차 오류")

    invalid_lag = data.apply(
        lambda row: _add_months(row["원자료_기준연월"], 2)
        != row["계약연월"],
        axis=1,
    )

    if invalid_lag.any():
        raise ValueError("KOSIS 기준연월 오류")

    values = data.melt(
        id_vars=["계약연월", "원자료_기준연월", "잠정치포함여부"],
        value_vars=list(FEATURE_COLUMNS),
        var_name="source_feature",
        value_name="value",
    )
    values["value"] = pd.to_numeric(values["value"], errors="coerce")
    values = values.dropna(subset=["value"]).copy()
    values["feature_name"] = values["source_feature"].map(FEATURE_COLUMNS)
    values["provisional"] = (
        values["잠정치포함여부"].eq("Y").astype(int)
    )
    result = values.rename(
        columns={
            "계약연월": "contract_month",
            "원자료_기준연월": "base_month",
        }
    )[
        [
            "contract_month",
            "base_month",
            "feature_name",
            "value",
            "provisional",
        ]
    ]

    if result.duplicated(["contract_month", "feature_name"]).any():
        raise ValueError("KOSIS Feature 중복")

    return result.sort_values(["contract_month", "feature_name"])


def _add_months(value: str, months: int) -> str:
    year, month = map(int, value.split("-"))
    index = year * 12 + month - 1 + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


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
            CREATE TABLE kosis_value (
                contract_month TEXT NOT NULL,
                base_month TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                value REAL NOT NULL,
                provisional INTEGER NOT NULL,
                PRIMARY KEY (contract_month, feature_name)
            );
            CREATE INDEX idx_kosis_lookup
                ON kosis_value (contract_month, feature_name);
            """
        )
        metadata = {
            "version": "kosis-v1",
            "source": source.name,
            "rows": str(len(values)),
        }
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            metadata.items(),
        )
        connection.executemany(
            "INSERT INTO kosis_value VALUES (?, ?, ?, ?, ?)",
            values.itertuples(index=False, name=None),
        )


def main() -> None:
    args = parse_args()

    if not args.source.is_file():
        raise FileNotFoundError(f"KOSIS 원천 없음: {args.source}")

    values = load_values(args.source)
    write_database(args.source, args.output, values)
    months = values["contract_month"].drop_duplicates()
    print(f"KOSIS Store 생성 완료: {args.output}")
    print(f"- rows: {len(values)}")
    print(f"- months: {len(months)}")
    print(f"- range: {months.iloc[0]} ~ {months.iloc[-1]}")


if __name__ == "__main__":
    main()
