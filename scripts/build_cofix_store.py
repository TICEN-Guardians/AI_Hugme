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
    columns = ["공시일", "대상연월", "신규취급액기준_COFIX"]
    data = pd.read_csv(source, usecols=columns, encoding="utf-8-sig")
    data["publication_date"] = pd.to_datetime(
        data["공시일"],
        errors="coerce",
    )
    data["value"] = pd.to_numeric(
        data["신규취급액기준_COFIX"],
        errors="coerce",
    )
    data = data.dropna(subset=["publication_date", "value"]).copy()
    data["publication_date"] = data["publication_date"].dt.date.astype(str)
    data["target_month"] = data["대상연월"].astype(str).str[:7]
    result = data[["publication_date", "target_month", "value"]]

    if result["publication_date"].duplicated().any():
        raise ValueError("COFIX 공시일 중복")

    return result.sort_values("publication_date")


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
            CREATE TABLE cofix_value (
                publication_date TEXT PRIMARY KEY,
                target_month TEXT NOT NULL,
                value REAL NOT NULL
            );
            """
        )
        metadata = {
            "version": "cofix-v1",
            "source": source.name,
            "rows": str(len(values)),
        }
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            metadata.items(),
        )
        connection.executemany(
            "INSERT INTO cofix_value VALUES (?, ?, ?)",
            values.itertuples(index=False, name=None),
        )


def main() -> None:
    args = parse_args()

    if not args.source.is_file():
        raise FileNotFoundError(f"COFIX 원천 없음: {args.source}")

    values = load_values(args.source)
    write_database(args.source, args.output, values)
    print(f"COFIX Store 생성 완료: {args.output}")
    print(f"- rows: {len(values)}")
    print(f"- range: {values.iloc[0]['publication_date']} ~ "
          f"{values.iloc[-1]['publication_date']}")


if __name__ == "__main__":
    main()
