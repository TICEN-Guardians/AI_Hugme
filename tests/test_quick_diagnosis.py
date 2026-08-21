import unittest
from datetime import date
from types import SimpleNamespace

from pydantic import ValidationError

from app.diagnosis.forced_warning import ForcedWarningInput, ForcedWarningRule
from app.diagnosis.report_builder import build_report_detail
from app.diagnosis.risk_indicator import RiskIndicatorCalculator
from app.diagnosis.risk_rule import RiskRule, RiskSeverityInput
from app.diagnosis.schemas import DiagnosisRequest, ValuationReliability


def quick_request() -> DiagnosisRequest:
    return DiagnosisRequest(
        analysisId=1,
        mode="QUICK",
        address="서울특별시 중구 세종대로 110",
        hoName="101호",
        deposit=100_000_000,
        contractDate=date(2026, 8, 21),
        exclusiveArea="59.83",
    )


class QuickDiagnosisTest(unittest.TestCase):
    def test_excludes_registry_missing_checks(self) -> None:
        indicators = RiskIndicatorCalculator.calculate(
            estimated_sale_price=200_000_000,
            estimated_lease_price=120_000_000,
            deposit=100_000_000,
            active_max_claim_amount=None,
            collateral_expected=False,
        )
        score = RiskRule.score(
            indicators,
            RiskSeverityInput(0.0, 0.0, 0.0, 0.0, 0.0),
        )
        warning = ForcedWarningRule.apply(
            score.grade,
            ForcedWarningInput(None, None, None, None, None, None, None, None),
            registry_required=False,
        )

        self.assertEqual(indicators.missing_checks, ())
        self.assertFalse(score.provisional_collateral_basis)
        self.assertEqual(warning.warnings, ())
        self.assertEqual(warning.missing_checks, ())

    def test_report_omits_collateral_and_recommends_detailed(self) -> None:
        request = quick_request()
        indicators = RiskIndicatorCalculator.calculate(
            estimated_sale_price=200_000_000,
            estimated_lease_price=120_000_000,
            deposit=request.deposit,
            active_max_claim_amount=None,
            collateral_expected=False,
        )
        score = RiskRule.score(
            indicators,
            RiskSeverityInput(0.0, 0.0, 0.0, 0.0, 0.0),
        )
        forced = ForcedWarningRule.apply(
            score.grade,
            ForcedWarningInput(None, None, None, None, None, None, None, None),
            registry_required=False,
        )
        result = SimpleNamespace(
            risk_indicators=indicators,
            risk_score=score,
            forced_warning=forced,
            missing_checks=(),
            estimated_sale_price=200_000_000,
            estimated_lease_price=120_000_000,
            warnings=(),
            fallback_features=(),
        )

        report = build_report_detail(
            request,
            result,
            ValuationReliability.HIGH,
        )

        self.assertEqual(report.title, "간편 전세 위험도 진단 결과")
        self.assertNotIn("collateral", {section.key for section in report.sections})
        self.assertEqual(report.notices, [])
        self.assertEqual(report.price_scenarios, [])
        self.assertEqual(
            report.explanation.recommended_actions[0].label,
            "정밀진단으로 추가 확인",
        )

    def test_detailed_requires_registry_payload(self) -> None:
        with self.assertRaises(ValidationError):
            DiagnosisRequest(
                analysisId=1,
                mode="DETAILED",
                address="서울특별시 중구 세종대로 110",
                hoName="101호",
                deposit=100_000_000,
                contractDate=date(2026, 8, 21),
                exclusiveArea="59.83",
            )
