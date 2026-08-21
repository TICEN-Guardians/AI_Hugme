from dataclasses import dataclass

from app.diagnosis.schemas import RiskGrade


GRADE_ORDER = {
    RiskGrade.LOW: 0,
    RiskGrade.MEDIUM: 1,
    RiskGrade.HIGH: 2,
    RiskGrade.CRITICAL: 3,
}


@dataclass(frozen=True)
class ForcedWarningInput:
    seizure: bool | None
    provisional_seizure: bool | None
    provisional_disposition: bool | None
    auction_commenced: bool | None
    trust_registration: bool | None
    senior_lease_right: bool | None
    owner_matches_contract_party: bool | None
    bad_landlord_matched: bool | None


@dataclass(frozen=True)
class ForcedWarningResult:
    grade: RiskGrade
    warnings: tuple[str, ...]
    missing_checks: tuple[str, ...]
    grade_overridden: bool


class ForcedWarningRule:
    @classmethod
    def apply(
        cls,
        grade: RiskGrade,
        values: ForcedWarningInput,
        registry_required: bool,
    ) -> ForcedWarningResult:
        if not registry_required:
            return ForcedWarningResult(
                grade=grade,
                warnings=(),
                missing_checks=(),
                grade_overridden=False,
            )

        warnings: set[str] = set()
        missing: set[str] = set()
        minimum_grade = grade

        rights = {
            "seizure": "SEIZURE",
            "provisional_seizure": "PROVISIONAL_SEIZURE",
            "provisional_disposition": "PROVISIONAL_DISPOSITION",
            "auction_commenced": "AUCTION_COMMENCED",
            "trust_registration": "TRUST_REGISTRATION",
            "senior_lease_right": "SENIOR_LEASE_RIGHT",
        }
        for field, code in rights.items():
            value = getattr(values, field)
            if value is True:
                warnings.add(code)
            elif value is None:
                missing.add(code)

        if values.auction_commenced is True:
            minimum_grade = cls._higher(minimum_grade, RiskGrade.CRITICAL)
        if values.senior_lease_right is True:
            minimum_grade = cls._higher(minimum_grade, RiskGrade.HIGH)

        if values.owner_matches_contract_party is False:
            warnings.add("OWNER_MISMATCH")
            minimum_grade = cls._higher(minimum_grade, RiskGrade.CRITICAL)
        elif values.owner_matches_contract_party is None:
            missing.add("OWNER_MATCH")

        if values.bad_landlord_matched is True:
            warnings.add("BAD_LANDLORD_MATCH")
            minimum_grade = cls._higher(minimum_grade, RiskGrade.HIGH)
        elif values.bad_landlord_matched is None:
            missing.add("BAD_LANDLORD_WATCHLIST")

        return ForcedWarningResult(
            grade=minimum_grade,
            warnings=tuple(sorted(warnings)),
            missing_checks=tuple(sorted(missing)),
            grade_overridden=minimum_grade != grade,
        )

    @staticmethod
    def _higher(current: RiskGrade, required: RiskGrade) -> RiskGrade:
        if GRADE_ORDER[required] > GRADE_ORDER[current]:
            return required
        return current
