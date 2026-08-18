from dataclasses import dataclass

from app.diagnosis.forced_warning import ForcedWarningInput
from app.diagnosis.schemas import (
    RegistryParseConfidence,
    RegistryParseStatus,
    RegistryRiskPayload,
    TriStateValue,
    WatchlistCheckStatus,
)


@dataclass(frozen=True)
class RegistryRiskContext:
    active_max_claim_amount: int | None
    forced_warning_input: ForcedWarningInput


class RegistryRiskAdapter:
    @classmethod
    def adapt(cls, payload: RegistryRiskPayload | None) -> RegistryRiskContext:
        if payload is None:
            return RegistryRiskContext(
                active_max_claim_amount=None,
                forced_warning_input=ForcedWarningInput(
                    None, None, None, None, None, None, None, None
                ),
            )

        claim_amount = payload.total_active_max_claim_amount
        if (
            payload.parse_status != RegistryParseStatus.SUCCESS
            or payload.parse_confidence
            not in {RegistryParseConfidence.HIGH, RegistryParseConfidence.MEDIUM}
        ):
            claim_amount = None

        senior_lease = cls._any_true(
            payload.has_active_jeonse_right,
            payload.has_active_leasehold_registration,
        )
        landlord_matched = None
        if payload.watchlist_check_status == WatchlistCheckStatus.CHECKED:
            landlord_matched = payload.bad_landlord_matched

        return RegistryRiskContext(
            active_max_claim_amount=claim_amount,
            forced_warning_input=ForcedWarningInput(
                seizure=cls._bool(payload.seizure),
                provisional_seizure=cls._bool(payload.provisional_seizure),
                provisional_disposition=cls._bool(
                    payload.provisional_disposition
                ),
                auction_commenced=cls._bool(payload.auction_commenced),
                trust_registration=cls._bool(payload.trust_registration),
                senior_lease_right=senior_lease,
                owner_matches_contract_party=cls._bool(
                    payload.owner_matches_contract_party
                ),
                bad_landlord_matched=landlord_matched,
            ),
        )

    @staticmethod
    def _bool(value: TriStateValue) -> bool | None:
        if value == TriStateValue.TRUE:
            return True
        if value == TriStateValue.FALSE:
            return False
        return None

    @classmethod
    def _any_true(
        cls,
        first: TriStateValue,
        second: TriStateValue,
    ) -> bool | None:
        values = (cls._bool(first), cls._bool(second))
        if True in values:
            return True
        if values == (False, False):
            return False
        return None
