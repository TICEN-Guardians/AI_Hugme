from typing import Any


class BuildingLedgerSelectionError(ValueError):
    pass


class BuildingLedgerSelector:
    NAME_SUFFIXES = (
        "아파트",
        "오피스텔",
        "연립주택",
        "다세대주택",
        "빌라",
    )

    @classmethod
    def matches_building_name(
        cls,
        expected: object,
        actual: object,
    ) -> bool:
        expected_name = cls._clean(expected)
        actual_name = cls._clean(actual)

        if not expected_name or not actual_name:
            return True

        if expected_name in actual_name:
            return True

        return cls._drop_suffix(expected_name) in actual_name

    @classmethod
    def _drop_suffix(cls, name: str) -> str:
        for suffix in cls.NAME_SUFFIXES:
            if name.endswith(suffix) and len(name) > len(suffix):
                return name[: -len(suffix)]

        return name

    @classmethod
    def select_title(
        cls,
        items: list[dict[str, Any]],
        building_name: str | None,
        dong_name: str | None,
    ) -> dict[str, Any]:
        candidates = [
            item
            for item in items
            if cls._is_main_building(item)
        ]

        if cls._clean(building_name):
            candidates = [
                item
                for item in candidates
                if cls._matches_building(item, building_name)
            ]

        if cls._dong(dong_name):
            candidates = [
                item
                for item in candidates
                if cls._matches_dong(item, dong_name)
            ]

        if not candidates:
            raise BuildingLedgerSelectionError(
                "일치하는 건축물대장 표제부 없음"
            )

        if len(candidates) > 1:
            if not cls._dong(dong_name) and any(
                cls._dong(item.get("dongNm"))
                for item in candidates
            ):
                raise BuildingLedgerSelectionError(
                    "공동주택 동 정보 필요"
                )

            raise BuildingLedgerSelectionError(
                f"건축물대장 표제부 후보 다수: "
                f"{len(candidates)}건"
            )

        return candidates[0]

    @staticmethod
    def _is_main_building(
        item: dict[str, Any],
    ) -> bool:
        return (
            item.get("mainAtchGbCdNm")
            == "주건축물"
        )

    @classmethod
    def _matches_building(
        cls,
        item: dict[str, Any],
        building_name: str | None,
    ) -> bool:
        return cls.matches_building_name(
            expected=building_name,
            actual=item.get("bldNm"),
        )

    @classmethod
    def _matches_dong(
        cls,
        item: dict[str, Any],
        dong_name: str | None,
    ) -> bool:
        expected = cls._dong(dong_name)
        actual = cls._dong(item.get("dongNm"))

        return bool(expected) and expected == actual

    @staticmethod
    def _dong(value: Any) -> str:
        text = BuildingLedgerSelector._clean(value)

        if text.endswith("동"):
            return text[:-1]

        return text

    @staticmethod
    def _clean(value: Any) -> str:
        if value is None:
            return ""

        return "".join(str(value).split()).lower()
