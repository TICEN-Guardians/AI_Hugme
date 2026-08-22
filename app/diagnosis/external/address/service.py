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


class AddressAmbiguousError(AddressResolutionError):
    def __init__(
        self,
        candidates: tuple[dict, ...],
    ) -> None:
        super().__init__(
            f"주소 검색 결과 다수: {len(candidates)}건"
        )
        self.candidates = candidates


class AddressService:
    def __init__(
        self,
        client: AddressClient,
    ) -> None:
        self.client = client

    def suggest(
        self,
        keyword: str,
        limit: int = 10,
    ) -> tuple[dict, ...]:
        return self.client.search(
            keyword,
            count_per_page=limit,
        ).items

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

        for normalize in (cls._plain, cls._normalize):
            expected = normalize(keyword)
            matches = [
                item
                for item in items
                if expected
                in {
                    normalize(item.get("roadAddr")),
                    normalize(item.get("roadAddrPart1")),
                    normalize(item.get("jibunAddr")),
                }
            ]

            if len(matches) == 1:
                return matches[0]

        raise AddressAmbiguousError(items)

    @staticmethod
    def _plain(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _normalize(value: object) -> str:
        text = re.sub(
            r"\s*\([^)]*\)\s*$",
            "",
            str(value or "").strip(),
        )
        return " ".join(text.split())
