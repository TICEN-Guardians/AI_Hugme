import html
from typing import Any

from app.diagnosis.external.address.schemas import (
    ResolvedAddress,
)
from app.diagnosis.external.building_ledger.schemas import (
    BuildingLedgerKey,
)


class AddressMappingError(ValueError):
    pass


class AddressMapper:
    @classmethod
    def map_result(
        cls,
        item: dict[str, Any],
    ) -> ResolvedAddress:
        legal_dong_code = cls._required(
            item,
            "admCd",
        )

        if (
            len(legal_dong_code) != 10
            or not legal_dong_code.isdigit()
        ):
            raise AddressMappingError(
                "법정동코드 형식 오류"
            )

        main_number = cls._number(
            item,
            "lnbrMnnm",
        )
        sub_number = cls._number(
            item,
            "lnbrSlno",
            default="0",
        )

        key = BuildingLedgerKey(
            sigungu_code=legal_dong_code[:5],
            bjdong_code=legal_dong_code[5:],
            plat_code=cls._plat_code(item.get("mtYn")),
            bun=main_number.zfill(4),
            ji=sub_number.zfill(4),
        )

        district_parts = [
            item.get("siNm"),
            item.get("sggNm"),
            item.get("emdNm"),
            item.get("liNm"),
        ]

        district = " ".join(
            str(value).strip()
            for value in district_parts
            if value and str(value).strip()
        )

        return ResolvedAddress(
            road_address=cls._required(
                item,
                "roadAddr",
            ),
            jibun_address=cls._required(
                item,
                "jibunAddr",
            ),
            legal_dong_code=legal_dong_code,
            district=district,
            building_name=cls._optional(
                item.get("bdNm")
            ),
            available_dongs=cls._dongs(
                item.get("detBdNmList")
            ),
            building_ledger_key=key,
        )

    @staticmethod
    def _required(
        item: dict[str, Any],
        name: str,
    ) -> str:
        value = str(item.get(name, "")).strip()

        if not value:
            raise AddressMappingError(
                f"주소 필수값 누락: {name}"
            )

        return value

    @classmethod
    def _number(
        cls,
        item: dict[str, Any],
        name: str,
        default: str | None = None,
    ) -> str:
        value = str(
            item.get(name, default or "")
        ).strip()

        if not value.isdigit():
            raise AddressMappingError(
                f"지번 형식 오류: {name}"
            )

        if len(value) > 4:
            raise AddressMappingError(
                f"지번 길이 오류: {name}"
            )

        return value

    @staticmethod
    def _plat_code(value: Any) -> str:
        return "1" if str(value).strip() == "1" else "0"

    @staticmethod
    def _optional(value: Any) -> str | None:
        text = html.unescape(str(value or "")).strip()
        return text or None

    @staticmethod
    def _dongs(value: Any) -> tuple[str, ...]:
        if not value:
            return ()

        return tuple(
            name.strip()
            for name in str(value).split(",")
            if name.strip()
        )