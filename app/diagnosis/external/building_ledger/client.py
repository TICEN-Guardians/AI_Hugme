from typing import Any
from urllib.parse import unquote
import requests

from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)


class BuildingLedgerApiError(RuntimeError):
    pass


class BuildingLedgerClient:
    BASE_URL = (
        "https://apis.data.go.kr/1613000/"
        "BldRgstHubService"
    )

    def __init__(
        self,
        service_key: str,
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        if not service_key:
            raise ValueError("건축물대장 API 키 누락")

        self.service_key = unquote(service_key.strip())
        self.timeout = timeout
        self.session = session or requests.Session()

    def get_title(
        self,
        key: BuildingLedgerKey,
    ) -> list[dict[str, Any]]:
        return self._get(
            endpoint="getBrTitleInfo",
            key=key,
        )

    def get_recap_title(
        self,
        key: BuildingLedgerKey,
    ) -> list[dict[str, Any]]:
        return self._get(
            endpoint="getBrRecapTitleInfo",
            key=key,
        )

    def _get(
        self,
        endpoint: str,
        key: BuildingLedgerKey,
    ) -> list[dict[str, Any]]:
        params = {
            "serviceKey": self.service_key,
            **key.to_params(),
            "numOfRows": "100",
            "pageNo": "1",
            "_type": "json",
        }

        try:
            response = self.session.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            status = (
                exc.response.status_code
                if exc.response is not None
                else "연결 오류"
            )

            raise BuildingLedgerApiError(
                f"건축물대장 API 호출 실패: {status}"
            ) from None
        except ValueError:
            raise BuildingLedgerApiError(
                "건축물대장 JSON 변환 실패"
            ) from None

        return self._items(payload)

    @staticmethod
    def _items(
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        api_response = payload.get("response", {})
        header = api_response.get("header", {})
        result_code = str(
            header.get("resultCode", "")
        )

        if result_code not in {"00", "000", "0"}:
            message = header.get(
                "resultMsg",
                "알 수 없는 오류",
            )
            raise BuildingLedgerApiError(
                f"건축물대장 API 오류: {message}"
            )

        body = api_response.get("body", {})
        items = body.get("items")

        if not items:
            return []

        item = items.get("item", [])

        if isinstance(item, dict):
            return [item]

        if isinstance(item, list):
            return item

        raise BuildingLedgerApiError(
            "건축물대장 응답 형식 오류"
        )