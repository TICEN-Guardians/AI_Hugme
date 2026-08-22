from dataclasses import dataclass

from app.diagnosis.risk_rule import RiskRule
from app.diagnosis.schemas import RiskGrade


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
    score: int
    grade: RiskGrade
    warnings: tuple[str, ...]
    missing_checks: tuple[str, ...]
    score_floor: int | None
    score_floor_applied: bool
    floor_reasons: tuple[str, ...]


class ForcedWarningRule:
    SCORE_FLOOR = 80

    @classmethod
    def apply(
        cls,
        score: int,
        values: ForcedWarningInput,
        registry_required: bool,
    ) -> ForcedWarningResult:
        if not registry_required:
            return ForcedWarningResult(
                score=score,
                grade=RiskRule.grade(score),
                warnings=(),
                missing_checks=(),
                score_floor=None,
                score_floor_applied=False,
                floor_reasons=(),
            )

        warnings: set[str] = set()
        missing: set[str] = set()
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

        if values.owner_matches_contract_party is False:
            warnings.add("OWNER_MISMATCH")
        elif values.owner_matches_contract_party is None:
            missing.add("OWNER_MATCH")

        if values.bad_landlord_matched is True:
            warnings.add("BAD_LANDLORD_MATCH")
        elif values.bad_landlord_matched is None:
            missing.add("BAD_LANDLORD_WATCHLIST")

        floor_reasons = tuple(sorted(warnings))
        score_floor = cls.SCORE_FLOOR if floor_reasons else None
        final_score = max(score, score_floor or 0)

        return ForcedWarningResult(
            score=final_score,
            grade=RiskRule.grade(final_score),
            warnings=tuple(sorted(warnings)),
            missing_checks=tuple(sorted(missing)),
            score_floor=score_floor,
            score_floor_applied=final_score != score,
            floor_reasons=floor_reasons,
        )
