import os

import psycopg2


def get_market_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(
            os.environ.get("POSTGRES_PORT")
            or os.environ.get("POSTGRES_HOST_PORT", "5432")
        ),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
