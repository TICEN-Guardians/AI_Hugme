from app.diagnosis.schemas import (
    DiagnosisRequest,
    PriceScenarioPoint,
    ReportDetail,
    ReportExplanation,
    ReportMetric,
    ReportNotice,
    ReportSection,
    RiskGrade,
)


GRADE_LABELS = {
    RiskGrade.LOW: "낮음",
    RiskGrade.MEDIUM: "보통",
    RiskGrade.HIGH: "높음",
    RiskGrade.CRITICAL: "매우 높음",
}

NOTICE_TEXT = {
    "SENIOR_LEASE_RIGHT": (
        "선순위 전세권 확인",
        "등기부에서 현재 유효한 선순위 전세권이 확인됐습니다.",
        "HIGH",
    ),
    "OWNER_MISMATCH": (
        "임대인과 소유자 불일치",
        "계약 상대방과 등기부의 현재 소유자가 일치하지 않습니다.",
        "CRITICAL",
    ),
    "BAD_LANDLORD_MATCHED": (
        "악성임대인 명단 일치",
        "현재 소유자가 악성임대인 확인 대상과 일치합니다.",
        "CRITICAL",
    ),
    "AUCTION_COMMENCED": (
        "경매개시 확인",
        "등기부에서 현재 유효한 경매개시 기록이 확인됐습니다.",
        "CRITICAL",
    ),
    "SEIZURE": (
        "압류 확인",
        "등기부에서 현재 유효한 압류 기록이 확인됐습니다.",
        "HIGH",
    ),
    "PROVISIONAL_SEIZURE": (
        "가압류 확인",
        "등기부에서 현재 유효한 가압류 기록이 확인됐습니다.",
        "HIGH",
    ),
    "PROVISIONAL_DISPOSITION": (
        "가처분 확인",
        "등기부에서 현재 유효한 가처분 기록이 확인됐습니다.",
        "HIGH",
    ),
    "TRUST_REGISTRATION": (
        "신탁등기 확인",
        "등기부에서 신탁등기가 확인되어 수탁자와 처분 권한 확인이 필요합니다.",
        "HIGH",
    ),
}

MISSING_TEXT = {
    "OWNER_MATCH": "계약 상대방과 등기 소유자의 일치 여부를 확인해 주세요.",
    "BAD_LANDLORD_WATCHLIST": "악성임대인 명단 조회 결과를 확인해 주세요.",
    "ACTIVE_MAX_CLAIM_AMOUNT": "활성 근저당 채권최고액을 확인해 주세요.",
}


def build_report_detail(request: DiagnosisRequest, result, reliability) -> ReportDetail:
    indicators = result.risk_indicators
    final_grade = result.forced_warning.grade
    notices = [notice(code) for code in result.forced_warning.warnings]
    notices.extend(
        ReportNotice(
            code=code,
            title="추가 확인 필요",
            description=MISSING_TEXT.get(code, f"{code} 항목을 확인해 주세요."),
            severity="INFO",
        )
        for code in result.missing_checks
    )

    sections = [
        ReportSection(
            key="valuation",
            title="시세 추정",
            description="입력 물건과 시장 데이터를 이용한 AI 추정 결과입니다.",
            metrics=[
                ReportMetric(key="salePrice", label="예상 매매가", value=result.estimated_sale_price, unit="원"),
                ReportMetric(key="leasePrice", label="예상 전세가", value=result.estimated_lease_price, unit="원"),
                ReportMetric(key="reliability", label="시세 신뢰도", value=reliability.value),
            ],
        ),
        ReportSection(
            key="collateral",
            title="보증금과 담보",
            description="보증금과 등기부상 활성 근저당을 매매가와 비교한 결과입니다.",
            metrics=[
                ReportMetric(key="deposit", label="계약 보증금", value=request.deposit, unit="원"),
                ReportMetric(key="collateralBurden", label="담보부담액", value=indicators.collateral_burden_amount, unit="원"),
                ReportMetric(key="collateralRate", label="담보부담률", value=percent(indicators.collateral_burden_rate), unit="%"),
                ReportMetric(key="shortfall", label="보증금 부족액", value=indicators.deposit_shortfall, unit="원"),
            ],
        ),
        ReportSection(
            key="riskScore",
            title="위험점수",
            description="확정된 규칙에 따라 계산한 위험요인별 점수입니다.",
            metrics=[
                ReportMetric(key="total", label="총점", value=result.risk_score.total, unit="점"),
                ReportMetric(key="underwater", label="깡통전세 위험", value=result.risk_score.underwater, unit="점"),
                ReportMetric(key="rollover", label="역전세 위험", value=result.risk_score.rollover, unit="점"),
                ReportMetric(key="property", label="주택 특성", value=result.risk_score.property, unit="점"),
                ReportMetric(key="market", label="시장 상황", value=result.risk_score.market, unit="점"),
            ],
        ),
    ]

    scenarios = [
        PriceScenarioPoint(
            label={"drop_0": "현재 시세", "drop_10": "매매가 10% 하락", "drop_20": "매매가 20% 하락"}.get(key, key),
            priceDropRate={"drop_0": 0, "drop_10": 10, "drop_20": 20}.get(key, 0),
            collateralBurdenRate=round(value * 100, 2),
        )
        for key, value in (indicators.price_drop_scenarios or {}).items()
    ]
    actions = recommended_actions(result)

    return ReportDetail(
        title="전세 위험도 진단 결과",
        gradeLabel=GRADE_LABELS[final_grade],
        sections=sections,
        notices=notices,
        priceScenarios=scenarios,
        explanation=ReportExplanation(
            summary=f"최종 전세 위험등급은 {GRADE_LABELS[final_grade]}입니다.",
            keyFindings=[
                f"예상 매매가는 {result.estimated_sale_price:,}원입니다.",
                f"담보부담률은 {percent(indicators.collateral_burden_rate) or 0:.2f}%입니다.",
                f"규칙 기반 위험점수는 {result.risk_score.total}점입니다.",
            ],
            cautions=[item.description for item in notices],
            recommendedActions=actions,
            generatedBy="RULE",
        ),
    )


def notice(code: str) -> ReportNotice:
    title, description, severity = NOTICE_TEXT.get(
        code,
        ("위험사항 확인", f"{code} 위험사항이 확인됐습니다.", "HIGH"),
    )
    return ReportNotice(code=code, title=title, description=description, severity=severity)


def percent(value: float | None) -> float | None:
    return round(value * 100, 2) if value is not None else None


def recommended_actions(result) -> list[str]:
    actions = ["계약 직전에 등기부등본을 다시 발급해 권리 변동을 확인하세요."]
    if result.forced_warning.warnings:
        actions.append("확인된 등기 위험이 해소되기 전에는 계약 진행을 보류하세요.")
    if result.missing_checks:
        actions.append("미확인 항목을 확인한 뒤 최종 계약 여부를 결정하세요.")
    actions.append("보증보험 가입 가능 여부와 예상 보증한도를 확인하세요.")
    return actions
