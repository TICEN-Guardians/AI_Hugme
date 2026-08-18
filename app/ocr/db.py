"""
Postgres(ParadeDB) 연결 설정.

.env 파일에서 DB 정보(hugme-postgre) 호출
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DB_CONFIG = {
    "host": os.environ.get(
        "POSTGRES_HOST",
        os.environ.get("DB_HOST", "localhost"),
    ),
    "port": int(
        os.environ.get(
            "POSTGRES_PORT",
            os.environ.get("DB_PORT", "5432"),
        )
    ),
    "dbname": os.environ.get(
        "POSTGRES_DB",
        os.environ.get("DB_NAME", "postgres"),
    ),
    "user": os.environ.get(
        "POSTGRES_USER",
        os.environ.get("DB_USER", "postgres"),
    ),
    "password": os.environ.get(
        "POSTGRES_PASSWORD",
        os.environ.get("DB_PASSWORD", "postgres"),
    ),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)
