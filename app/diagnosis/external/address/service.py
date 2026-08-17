import re

from app.diagnosis.external.address.client import (
    AddressClient,
)
from app.diagnosis.external.address.mapper import (
    AddressMapper,
)
from app.diagnosis.external.address.schemas import (
    ResolvedAddress,
)


class AddressResolutionError(ValueError):
    pass


class AddressService:
    def __init__(
        self,
        client: AddressClient,
    ) -> None:
        self.client = client

    def resolve(
        self,
        keyword: str,
    ) -> ResolvedAddress:
        result = self.client.search(keyword)

        if result.total_count == 0:
            raise AddressResolutionError(
                "일치하는 주소 없음"
            )

        if not result.items:
            raise AddressResolutionError(
                "주소 검색 결과 수 불일치"
            )

        item = self._select(keyword, result.items)

        return AddressMapper.map_result(
            item
        )

    @classmethod
    def _select(
        cls,
        keyword: str,
        items: tuple[dict, ...],
    ) -> dict:
        if len(items) == 1:
            return items[0]

        expected = cls._normalize(keyword)
        matches = [
            item
            for item in items
            if expected
            in {
                cls._normalize(item.get("roadAddr")),
                cls._normalize(item.get("roadAddrPart1")),
                cls._normalize(item.get("jibunAddr")),
            }
        ]

        if len(matches) == 1:
            return matches[0]

        raise AddressResolutionError(
            f"주소 검색 결과 다수: {len(items)}건"
        )

    @staticmethod
    def _normalize(value: object) -> str:
        text = re.sub(
            r"\s*\([^)]*\)\s*$",
            "",
            str(value or "").strip(),
        )
        return " ".join(text.split())
