from app.diagnosis.registry_risk_adapter import RegistryRiskAdapter
from app.diagnosis.schemas import (
    RegistryParseConfidence,
    RegistryRiskPayload,
)


def main() -> None:
    payload = RegistryRiskPayload.model_validate(
        {
            "parseStatus": "SUCCESS",
            "parseConfidence": "HIGH",
            "totalActiveMaxClaimAmount": 100_000_000,
            "seizure": "FALSE",
            "provisionalSeizure": "FALSE",
            "provisionalDisposition": "FALSE",
            "auctionCommenced": "FALSE",
            "trustRegistration": "FALSE",
            "hasActiveJeonseRight": "TRUE",
            "hasActiveLeaseholdRegistration": "FALSE",
            "ownerMatchesContractParty": "TRUE",
            "watchlistCheckStatus": "CHECKED",
            "badLandlordMatched": False,
        }
    )
    result = RegistryRiskAdapter.adapt(payload)
    assert result.active_max_claim_amount == 100_000_000
    assert result.forced_warning_input.senior_lease_right is True
    assert result.forced_warning_input.bad_landlord_matched is False

    low = payload.model_copy(
        update={"parse_confidence": RegistryParseConfidence.LOW}
    )
    low = RegistryRiskPayload.model_validate(low.model_dump(by_alias=True))
    assert RegistryRiskAdapter.adapt(low).active_max_claim_amount is None

    missing = RegistryRiskAdapter.adapt(None)
    assert missing.active_max_claim_amount is None
    assert missing.forced_warning_input.auction_commenced is None

    print("등기 위험 Adapter 검증 완료")
    print(f"- 채권최고액: {result.active_max_claim_amount}")
    print(f"- 선순위 권리: {result.forced_warning_input.senior_lease_right}")
    print(f"- 악성임대인: {result.forced_warning_input.bad_landlord_matched}")
    print(f"- 낮은 파싱 신뢰도 채권최고액: {RegistryRiskAdapter.adapt(low).active_max_claim_amount}")


if __name__ == "__main__":
    main()
