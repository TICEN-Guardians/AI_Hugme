import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INFRA_ENV_PATH = PROJECT_ROOT.parent / "Infra_Hugme" / ".env"

load_dotenv(INFRA_ENV_PATH)

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client

    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = AsyncOpenAI(api_key=api_key)
    return _client
