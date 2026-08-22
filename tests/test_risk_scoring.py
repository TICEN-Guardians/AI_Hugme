import unittest
from dataclasses import replace

from app.diagnosis.forced_warning import ForcedWarningInput, ForcedWarningRule
from app.diagnosis.risk_indicator import RiskIndicatorCalculator
from app.diagnosis.risk_rule import RiskRule, RiskSeverityInput
from app.diagnosis.schemas import RiskGrade


def registry_values() -> ForcedWarningInput:
    return ForcedWarningInput(
        seizure=False,
        provisional_seizure=False,
        provisional_disposition=False,
        auction_commenced=False,
        trust_registration=False,
        senior_lease_right=False,
        owner_matches_contract_party=True,
        bad_landlord_matched=False,
    )


class RiskScoringTest(unittest.TestCase):
    def test_grade_boundaries(self) -> None:
        expected = {
            0: RiskGrade.LOW,
            25: RiskGrade.LOW,
            26: RiskGrade.MEDIUM,
            55: RiskGrade.MEDIUM,
            56: RiskGrade.HIGH,
            79: RiskGrade.HIGH,
            80: RiskGrade.CRITICAL,
            100: RiskGrade.CRITICAL,
        }
        for score, grade in expected.items():
            with self.subTest(score=score):
                self.assertEqual(RiskRule.grade(score), grade)

    def test_price_policy_floors(self) -> None:
        self.assertEqual(
            RiskRule.policy_floor(1.01, 0.0),
            (100, ("RECOVERY_SHORTFALL",)),
        )
        self.assertEqual(
            RiskRule.policy_floor(1.0, 0.0),
            (80, ("NO_RECOVERY_BUFFER",)),
        )
        self.assertEqual(
            RiskRule.policy_floor(0.7, 0.25),
            (80, ("EXTREME_LEASE_DEVIATION",)),
        )
        self.assertEqual(
            RiskRule.policy_floor(0.8, 0.05),
            (56, ("COMBINED_PRICE_RISK",)),
        )

    def test_detailed_score_uses_active_mortgage_amount(self) -> None:
        quick = RiskIndicatorCalculator.calculate(
            estimated_sale_price=100_000_000,
            estimated_lease_price=80_000_000,
            deposit=60_000_000,
            active_max_claim_amount=None,
            collateral_expected=False,
        )
        detailed = RiskIndicatorCalculator.calculate(
            estimated_sale_price=100_000_000,
            estimated_lease_price=80_000_000,
            deposit=60_000_000,
            active_max_claim_amount=30_000_000,
            collateral_expected=True,
        )
        severity = RiskSeverityInput(0.0, 0.0)

        quick_score = RiskRule.score(quick, severity)
        detailed_score = RiskRule.score(detailed, severity)

        self.assertEqual(quick_score.price_burden, 0)
        self.assertEqual(detailed_score.price_burden, 40)
        self.assertGreater(detailed_score.total, quick_score.total)

    def test_each_blocking_registry_risk_sets_score_floor(self) -> None:
        fields = {
            "seizure": "SEIZURE",
            "provisional_seizure": "PROVISIONAL_SEIZURE",
            "provisional_disposition": "PROVISIONAL_DISPOSITION",
            "auction_commenced": "AUCTION_COMMENCED",
            "trust_registration": "TRUST_REGISTRATION",
            "senior_lease_right": "SENIOR_LEASE_RIGHT",
            "bad_landlord_matched": "BAD_LANDLORD_MATCH",
        }
        for field, code in fields.items():
            with self.subTest(field=field):
                result = ForcedWarningRule.apply(
                    20,
                    replace(registry_values(), **{field: True}),
                    registry_required=True,
                )
                self.assertEqual(result.score, 80)
                self.assertEqual(result.grade, RiskGrade.CRITICAL)
                self.assertEqual(result.floor_reasons, (code,))

        owner_mismatch = ForcedWarningRule.apply(
            20,
            replace(registry_values(), owner_matches_contract_party=False),
            registry_required=True,
        )
        self.assertEqual(owner_mismatch.score, 80)
        self.assertEqual(owner_mismatch.grade, RiskGrade.CRITICAL)
        self.assertEqual(owner_mismatch.floor_reasons, ("OWNER_MISMATCH",))


if __name__ == "__main__":
    unittest.main()
