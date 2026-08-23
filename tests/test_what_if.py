import unittest

from app.diagnosis.schemas import DiagnosisMode, RiskGrade
from app.diagnosis.what_if import DiagnosisWhatIfCalculator


class DiagnosisWhatIfCalculatorTest(unittest.TestCase):
    def test_quick_scenario_recalculates_existing_price_rules(self) -> None:
        result = DiagnosisWhatIfCalculator.calculate(
            mode=DiagnosisMode.QUICK,
            estimated_sale_price=400_000_000,
            estimated_lease_price=180_000_000,
            baseline_deposit=200_000_000,
            scenario_deposit=180_000_000,
            sale_price_drop_rate=10,
            lease_price_drop_rate=0,
            active_max_claim_amount=None,
            remove_active_mortgage=False,
            market_trend_score=0,
            unresolved_risk_reasons=(),
        )

        self.assertEqual(result.baseline.final_score, 31)
        self.assertEqual(result.scenario.final_score, 14)
        self.assertEqual(result.scenario.final_grade, RiskGrade.LOW)
        self.assertEqual(result.score_change, -17)
        self.assertFalse(result.registry_blockers_remain)

    def test_detailed_scenario_can_remove_active_mortgage(self) -> None:
        result = DiagnosisWhatIfCalculator.calculate(
            mode=DiagnosisMode.DETAILED,
            estimated_sale_price=400_000_000,
            estimated_lease_price=180_000_000,
            baseline_deposit=200_000_000,
            scenario_deposit=200_000_000,
            sale_price_drop_rate=0,
            lease_price_drop_rate=0,
            active_max_claim_amount=200_000_000,
            remove_active_mortgage=True,
            market_trend_score=0,
            unresolved_risk_reasons=(),
        )

        self.assertEqual(
            result.baseline.active_max_claim_amount,
            200_000_000,
        )
        self.assertEqual(result.scenario.active_max_claim_amount, 0)
        self.assertLess(
            result.scenario.final_score,
            result.baseline.final_score,
        )

    def test_registry_blocker_keeps_final_score_floor(self) -> None:
        result = DiagnosisWhatIfCalculator.calculate(
            mode=DiagnosisMode.DETAILED,
            estimated_sale_price=400_000_000,
            estimated_lease_price=180_000_000,
            baseline_deposit=200_000_000,
            scenario_deposit=100_000_000,
            sale_price_drop_rate=0,
            lease_price_drop_rate=0,
            active_max_claim_amount=0,
            remove_active_mortgage=False,
            market_trend_score=0,
            unresolved_risk_reasons=("OWNER_MISMATCH",),
        )

        self.assertEqual(result.scenario.final_score, 80)
        self.assertEqual(result.scenario.final_grade, RiskGrade.CRITICAL)
        self.assertTrue(result.registry_blockers_remain)
        self.assertEqual(result.scenario.rights_adjustment, 80)


if __name__ == "__main__":
    unittest.main()
