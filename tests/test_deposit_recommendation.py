import unittest

from app.diagnosis.deposit_recommendation import (
    DepositRecommendationCalculator,
)
from app.diagnosis.risk_rule import RiskSeverityInput
from app.diagnosis.schemas import DiagnosisMode, RiskGrade


class DepositRecommendationTest(unittest.TestCase):
    def test_quick_limit_uses_existing_low_grade_boundary(self) -> None:
        result = DepositRecommendationCalculator.calculate(
            mode=DiagnosisMode.QUICK,
            estimated_sale_price=400_000_000,
            estimated_lease_price=180_000_000,
            current_deposit=200_000_000,
            active_max_claim_amount=None,
            severity=RiskSeverityInput(0.0, 0.0),
            unresolved_risk_reasons=(),
        )

        self.assertEqual(result.recommended_limit, 189_000_000)
        self.assertEqual(result.reduction_required, 11_000_000)
        self.assertEqual(result.target_grade, RiskGrade.LOW)
        self.assertEqual(result.target_score_max, 25)
        self.assertTrue(result.provisional)
        self.assertFalse(result.registry_reflected)

    def test_detailed_limit_reflects_active_mortgage(self) -> None:
        result = DepositRecommendationCalculator.calculate(
            mode=DiagnosisMode.DETAILED,
            estimated_sale_price=400_000_000,
            estimated_lease_price=180_000_000,
            current_deposit=200_000_000,
            active_max_claim_amount=200_000_000,
            severity=RiskSeverityInput(0.0, 0.0),
            unresolved_risk_reasons=(),
        )

        self.assertEqual(result.recommended_limit, 119_000_000)
        self.assertEqual(result.reduction_required, 81_000_000)
        self.assertTrue(result.registry_reflected)
        self.assertFalse(result.provisional)
        self.assertLessEqual(result.score_at_limit, 25)

    def test_registry_blocker_is_not_resolved_by_deposit_adjustment(self) -> None:
        result = DepositRecommendationCalculator.calculate(
            mode=DiagnosisMode.DETAILED,
            estimated_sale_price=400_000_000,
            estimated_lease_price=180_000_000,
            current_deposit=200_000_000,
            active_max_claim_amount=0,
            severity=RiskSeverityInput(0.0, 0.0),
            unresolved_risk_reasons=("OWNER_MISMATCH",),
        )

        self.assertFalse(result.adjustment_can_resolve_final_risk)
        self.assertEqual(
            result.unresolved_risk_reasons,
            ("OWNER_MISMATCH",),
        )


if __name__ == "__main__":
    unittest.main()
