import argparse
import sqlite3
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_values(source: Path) -> pd.DataFrame:
    columns = [
        "계약연월",
        "주담대금리_기준연월",
        "주담대금리_적용값",
        "주담대금리_잠정치여부",
        "주담대금리_가용여부",
    ]
    data = pd.read_csv(source, usecols=columns, encoding="utf-8-sig")
    data = data[data["주담대금리_가용여부"].eq("Y")].copy()
    data["value"] = pd.to_numeric(
        data["주담대금리_적용값"],
        errors="coerce",
    )
    data = data.dropna(
        subset=["계약연월", "주담대금리_기준연월", "value"]
    ).copy()
    data["provisional"] = (
        data["주담대금리_잠정치여부"].eq("Y").astype(int)
    )
    result = data.rename(
        columns={
            "계약연월": "contract_month",
            "주담대금리_기준연월": "base_month",
        }
    )[["contract_month", "base_month", "value", "provisional"]]

    if result["contract_month"].duplicated().any():
        raise ValueError("ECOS 계약연월 중복")

    invalid_lag = result.apply(
        lambda row: _next_month(row["base_month"]) != row["contract_month"],
        axis=1,
    )

    if invalid_lag.any():
        raise ValueError("ECOS 공표시차 오류")

    return result.sort_values("contract_month")


def _next_month(value: str) -> str:
    year, month = map(int, value.split("-"))

    if month == 12:
        return f"{year + 1:04d}-01"

    return f"{year:04d}-{month + 1:02d}"


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
            CREATE TABLE ecos_mortgage_rate (
                contract_month TEXT PRIMARY KEY,
                base_month TEXT NOT NULL,
                value REAL NOT NULL,
                provisional INTEGER NOT NULL
            );
            """
        )
        metadata = {
            "version": "ecos-v1",
            "source": source.name,
            "rows": str(len(values)),
        }
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            metadata.items(),
        )
        connection.executemany(
            "INSERT INTO ecos_mortgage_rate VALUES (?, ?, ?, ?)",
            values.itertuples(index=False, name=None),
        )


def main() -> None:
    args = parse_args()

    if not args.source.is_file():
        raise FileNotFoundError(f"ECOS 원천 없음: {args.source}")

    values = load_values(args.source)
    write_database(args.source, args.output, values)
    print(f"ECOS Store 생성 완료: {args.output}")
    print(f"- rows: {len(values)}")
    print(f"- range: {values.iloc[0]['contract_month']} ~ "
          f"{values.iloc[-1]['contract_month']}")


if __name__ == "__main__":
    main()
