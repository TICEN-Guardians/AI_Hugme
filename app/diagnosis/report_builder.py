from app.diagnosis.risk_rule import RiskRule
from app.diagnosis.schemas import (
    DiagnosisMode,
    DiagnosisRequest,
    PriceScenarioPoint,
    RegistryRiskPayload,
    ReportAction,
    ReportDetail,
    ReportExplanation,
    ReportFinding,
    ReportMetric,
    ReportNotice,
    ReportSection,
    RiskGrade,
    ValuationReliability,
)


GRADE_LABELS = {
    RiskGrade.LOW: "낮음",
    RiskGrade.MEDIUM: "보통",
    RiskGrade.HIGH: "주의",
    RiskGrade.CRITICAL: "위험",
}

RELIABILITY_LABELS = {
    ValuationReliability.HIGH: "높음",
    ValuationReliability.MEDIUM: "보통",
    ValuationReliability.LOW: "낮음",
}

MARKET_WARNING_PREFIXES = ("ECOS_", "KOSIS_", "RONE_")

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
    "BAD_LANDLORD_MATCH": (
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

PRICE_FLOOR_LABELS = {
    "RECOVERY_SHORTFALL": "담보부담액이 예상 매매가를 초과함",
    "NO_RECOVERY_BUFFER": "담보부담액이 예상 매매가와 같아 회수 여유가 없음",
    "EXTREME_LEASE_DEVIATION": "보증금이 예상 전세가보다 25% 이상 높음",
    "COMBINED_PRICE_RISK": "담보부담률 80% 이상과 전세시세 이탈 5% 이상이 함께 확인됨",
}

MISSING_TEXT = {
    "OWNER_MATCH": (
        "임대인·소유자 일치 미확인",
        "계약 상대방과 등기 소유자의 일치 여부를 확인해 주세요.",
    ),
    "BAD_LANDLORD_WATCHLIST": (
        "악성임대인 명단 조회 미완료",
        "악성임대인 명단 조회 결과를 확인해 주세요.",
    ),
    "ACTIVE_MAX_CLAIM_AMOUNT": (
        "근저당 채권최고액 미확인",
        "활성 근저당 채권최고액을 확인해 주세요.",
    ),
    "SEIZURE": (
        "압류 여부 미확인",
        "등기부에서 압류 기록 여부를 확인하지 못했습니다.",
    ),
    "PROVISIONAL_SEIZURE": (
        "가압류 여부 미확인",
        "등기부에서 가압류 기록 여부를 확인하지 못했습니다.",
    ),
    "PROVISIONAL_DISPOSITION": (
        "가처분 여부 미확인",
        "등기부에서 가처분 기록 여부를 확인하지 못했습니다.",
    ),
    "AUCTION_COMMENCED": (
        "경매개시 여부 미확인",
        "등기부에서 경매개시 기록 여부를 확인하지 못했습니다.",
    ),
    "TRUST_REGISTRATION": (
        "신탁등기 여부 미확인",
        "등기부에서 신탁등기 여부를 확인하지 못했습니다.",
    ),
    "SENIOR_LEASE_RIGHT": (
        "선순위 전세권 여부 미확인",
        "등기부에서 선순위 전세권·임차권등기 여부를 확인하지 못했습니다.",
    ),
}


PRICE_DROP_SCENARIOS = {
    "drop_0": (0, "현재 시세"),
    "drop_10": (10, "매매가 10% 하락"),
    "drop_20": (20, "매매가 20% 하락"),
}


def price_scenario(
    key: str,
    burden_rate: float,
    estimated_sale_price: int,
) -> PriceScenarioPoint:
    drop_rate, label = PRICE_DROP_SCENARIOS.get(key, (0, key))

    return PriceScenarioPoint(
        label=label,
        priceDropRate=drop_rate,
        estimatedSalePrice=round(
            estimated_sale_price * (1 - drop_rate / 100)
        ),
        collateralBurdenRate=round(burden_rate * 100, 2),
        verdict=RiskRule.dtv_verdict(burden_rate),
    )


def money(value: int | None) -> str:
    """리포트 문장에 넣을 한국식 금액 표기."""
    if value is None:
        return "확인 필요"

    sign = "-" if value < 0 else ""
    amount = abs(int(value))
    eok, rest = divmod(amount, 100_000_000)
    man = round(rest / 10_000)
    if man == 10_000:
        eok += 1
        man = 0

    if eok and man:
        return f"{sign}{eok}억 {man:,}만원"
    if eok:
        return f"{sign}{eok}억원"
    if man:
        return f"{sign}{man:,}만원"
    return f"{sign}{amount:,}원"


def rate_text(value: float | None) -> str:
    return "확인 필요" if value is None else f"{value * 100:.2f}%"


def josa(word: str, with_final: str, without_final: str) -> str:
    """앞 글자 받침에 맞는 조사를 고른다. 따옴표 같은 기호는 건너뛴다."""
    for char in reversed(word):
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            return with_final if (code - 0xAC00) % 28 else without_final
    return f"{without_final}({with_final})"


def owner_names(registry: RegistryRiskPayload | None) -> list[str]:
    if registry is None:
        return []
    return [
        name.strip()
        for name in registry.owner_names
        if name and name.strip()
    ]


def owner_label(names: list[str]) -> str:
    if not names:
        return ""
    head = "·".join(f"'{name}'" for name in names[:2])
    if len(names) > 2:
        return f"{head} 외 {len(names) - 2}명"
    return head


def contract_party(registry: RegistryRiskPayload | None) -> str | None:
    if registry is None or not registry.contract_party_name:
        return None
    return registry.contract_party_name.strip() or None


def owner_mismatch_text(registry: RegistryRiskPayload | None) -> str:
    party = contract_party(registry)
    names = owner_names(registry)

    if party and names:
        label = owner_label(names)
        return (
            f"계약 상대방으로 입력한 임대인 '{party}'{josa(party, '과', '와')} "
            f"등기부상 현재 소유자 {label}{josa(label, '이', '가')} 서로 다릅니다. "
            "소유자가 아닌 사람과 계약하면 보증금 반환 청구가 어려울 수 있습니다."
        )
    if names:
        return (
            f"등기부상 현재 소유자는 {owner_label(names)}입니다. "
            "계약 상대방이 이 소유자와 같은지 반드시 확인해 주세요."
        )
    return NOTICE_TEXT["OWNER_MISMATCH"][1]


def bad_landlord_text(registry: RegistryRiskPayload | None) -> str:
    names = owner_names(registry)
    if names:
        label = owner_label(names)
        return (
            f"등기부상 현재 소유자 {label}{josa(label, '이', '가')} "
            "악성임대인 확인 대상과 이름이 일치합니다."
        )
    return NOTICE_TEXT["BAD_LANDLORD_MATCH"][1]


def owner_match_missing_text(registry: RegistryRiskPayload | None) -> str:
    party = contract_party(registry)
    names = owner_names(registry)

    if names and not party:
        return (
            f"등기부상 현재 소유자는 {owner_label(names)}입니다. "
            "계약 상대방 이름을 입력하면 소유자 일치 여부를 확인해 드립니다."
        )
    if party and not names:
        return (
            f"입력한 임대인은 '{party}'입니다. "
            "등기부에서 소유자 이름을 읽지 못해 일치 여부를 확인하지 못했습니다."
        )
    return MISSING_TEXT["OWNER_MATCH"][1]


def notice(
    code: str,
    registry: RegistryRiskPayload | None = None,
) -> ReportNotice:
    title, description, severity = NOTICE_TEXT.get(
        code,
        ("위험사항 확인", f"{code} 위험사항이 확인됐습니다.", "HIGH"),
    )
    if code == "OWNER_MISMATCH":
        description = owner_mismatch_text(registry)
    elif code == "BAD_LANDLORD_MATCH":
        description = bad_landlord_text(registry)

    return ReportNotice(
        code=code,
        title=title,
        description=description,
        severity=severity,
    )


def missing_notice(
    code: str,
    registry: RegistryRiskPayload | None = None,
) -> ReportNotice:
    title, description = MISSING_TEXT.get(
        code,
        ("추가 확인 필요", f"{code} 항목을 확인해 주세요."),
    )
    if code == "OWNER_MATCH":
        description = owner_match_missing_text(registry)

    return ReportNotice(
        code=code,
        title=title,
        description=description,
        severity="INFO",
    )


def lease_gap_finding(deposit: int, lease: int, gap_rate: float) -> ReportFinding:
    diff = deposit - lease
    if diff > 0:
        description = (
            f"계약 보증금 {money(deposit)}이 AI 예상 전세가 {money(lease)}보다 "
            f"{money(diff)}({rate_text(gap_rate)}) 높습니다. "
            "만기에 같은 조건으로 다음 세입자를 구하기 어려워 반환 지연 위험이 커집니다."
        )
    elif diff < 0:
        description = (
            f"계약 보증금 {money(deposit)}이 AI 예상 전세가 {money(lease)}보다 "
            f"{money(-diff)}({rate_text(abs(gap_rate))}) 낮습니다. "
            "보증금이 전세시세보다 낮아 역전세로 보증금을 못 돌려받을 위험은 낮은 편입니다."
        )
    else:
        description = f"계약 보증금이 AI 예상 전세가 {money(lease)}와 같은 수준입니다."

    return ReportFinding(title="전세시세 괴리", description=description)


def collateral_finding(deposit: int, indicators) -> ReportFinding | None:
    burden = indicators.collateral_burden_amount
    if burden is None or indicators.collateral_burden_rate is None:
        return None

    mortgage = burden - deposit
    if mortgage > 0:
        lead = (
            f"선순위 근저당 채권최고액 {money(mortgage)}과 보증금 {money(deposit)}을 "
            f"더한 담보부담액 {money(burden)}"
        )
    else:
        lead = f"선순위 근저당이 없어 담보부담액은 보증금과 같은 {money(burden)}이며, 이 금액"

    return ReportFinding(
        title="담보부담률",
        description=(
            f"{lead}은 AI 예상 매매가의 "
            f"{rate_text(indicators.collateral_burden_rate)}입니다."
        ),
    )


def recovery_finding(deposit: int, indicators) -> ReportFinding | None:
    recoverable = indicators.recoverable_amount
    if recoverable is None:
        return None

    shortfall = indicators.deposit_shortfall or 0
    if shortfall > 0:
        description = (
            f"예상 매매가에서 선순위 채권을 뺀 회수 가능액은 {money(recoverable)}으로, "
            f"보증금 {money(deposit)}보다 {money(shortfall)} 부족합니다."
        )
    else:
        description = (
            f"예상 매매가에서 선순위 채권을 뺀 회수 가능액은 {money(recoverable)}으로, "
            f"보증금 {money(deposit)}보다 {money(recoverable - deposit)} 많습니다."
        )

    drop_20 = (indicators.price_drop_scenarios or {}).get("drop_20")
    if drop_20 is not None:
        description += (
            f" 매매가가 20% 하락해도 담보부담률은 {rate_text(drop_20)}로 안전 구간입니다."
            if RiskRule.dtv_verdict(drop_20) == "SAFE"
            else f" 매매가가 20% 하락하면 담보부담률은 {rate_text(drop_20)}가 됩니다."
        )

    return ReportFinding(title="보증금 회수 여력", description=description)


def reliability_finding(
    reliability: ValuationReliability,
    result,
) -> ReportFinding:
    label = RELIABILITY_LABELS[reliability]

    if reliability == ValuationReliability.LOW:
        detail = (
            f"예측에 쓰는 입력값 {len(result.fallback_features)}개를 "
            "지역 평균 등 대체값으로 채워 추정 매매가 오차가 클 수 있습니다. "
            "인근 실거래가를 함께 확인해 주세요."
        )
    elif reliability == ValuationReliability.MEDIUM:
        market = sum(
            1
            for code in result.warnings
            if code.startswith(MARKET_WARNING_PREFIXES)
        )
        ledger = len(result.warnings) - market
        parts = []
        if ledger:
            parts.append(f"건축물대장 항목 {ledger}건 미확인")
        if market:
            parts.append(f"시장지표 {market}건 지연·잠정치")
        reason = ", ".join(parts) if parts else "일부 데이터 품질 경고"
        detail = f"{reason}가 있어 추정치를 참고용으로 보셔야 합니다."
    else:
        detail = (
            "입력 특성과 시장 데이터가 모두 정상 범위여서 "
            "추정치를 그대로 참고할 수 있습니다."
        )

    return ReportFinding(
        title="시세 신뢰도",
        description=f"AI 시세 신뢰도는 {label}입니다. {detail}",
    )


def floor_reason_label(code: str) -> str:
    if code in PRICE_FLOOR_LABELS:
        return PRICE_FLOOR_LABELS[code]
    return NOTICE_TEXT.get(code, (code,))[0]


def score_finding(request: DiagnosisRequest, result) -> ReportFinding:
    score = result.risk_score
    final_score = result.forced_warning.score
    price_label = (
        "담보 회수부담"
        if request.mode == DiagnosisMode.DETAILED
        else "계약가격 부담"
    )
    adjustments = []
    if score.policy_adjustment:
        adjustments.append(f"가격 위험 하한 조정 +{score.policy_adjustment}점")
    rights_adjustment = final_score - score.total
    if rights_adjustment:
        adjustments.append(f"등기 권리 하한 조정 +{rights_adjustment}점")
    adjustment_text = (
        f" {', '.join(adjustments)}을 반영해 최종 {final_score}점입니다."
        if adjustments
        else f" 최종 위험점수도 {final_score}점입니다."
    )

    return ReportFinding(
        title="위험점수 구성",
        description=(
            f"기본 가중점수는 {score.base_total}점입니다. "
            f"{price_label} {score.price_burden}점, "
            f"주변 전세수준 이탈 {score.lease_market_deviation}점, "
            f"시장 추세 {score.market_trend}점을 합산했습니다."
            f"{adjustment_text}"
        ),
    )


def score_floor_finding(result) -> ReportFinding | None:
    if result.forced_warning.score == result.risk_score.base_total:
        return None

    reason_codes = dict.fromkeys(
        (
            *result.risk_score.floor_reasons,
            *result.forced_warning.floor_reasons,
        )
    )
    causes = ", ".join(floor_reason_label(code) for code in reason_codes)
    return ReportFinding(
        title="최종점수 조정 근거",
        description=(
            f"기본 가중점수 {result.risk_score.base_total}점에 "
            f"{causes} 최종 판정 규칙을 적용해 "
            f"{result.forced_warning.score}점으로 조정했습니다."
        ),
    )


def headline_risk_text(request: DiagnosisRequest, result) -> str:
    indicators = result.risk_indicators
    deposit = request.deposit
    shortfall = indicators.deposit_shortfall or 0

    if shortfall > 0:
        return (
            f"예상 매매가 기준으로 보증금 {money(deposit)} 가운데 "
            f"{money(shortfall)}은 회수하지 못할 수 있습니다."
        )
    if deposit > result.estimated_lease_price:
        return (
            f"계약 보증금 {money(deposit)}은 AI 예상 전세가 "
            f"{money(result.estimated_lease_price)}보다 "
            f"{money(deposit - result.estimated_lease_price)}"
            f"({rate_text(indicators.lease_price_gap_rate)}) 높아, "
            "만기에 같은 조건으로 다음 세입자를 구하지 못하면 "
            "임대인이 보증금을 바로 돌려주기 어려울 수 있습니다."
        )
    if indicators.collateral_burden_rate is not None:
        return (
            f"보증금과 선순위 채권을 합한 담보부담액은 예상 매매가의 "
            f"{rate_text(indicators.collateral_burden_rate)}입니다."
        )
    return (
        f"계약 보증금은 AI 예상 매매가의 "
        f"{rate_text(indicators.lease_to_sale_rate)}입니다."
    )


def summary_collateral_text(request: DiagnosisRequest, result) -> str | None:
    """회수 여력과 하락 시나리오를 한 문장으로 덧붙인다."""
    indicators = result.risk_indicators
    if indicators.recoverable_amount is None:
        return None

    # 담보부담률이 4%대인데 "여유가 빠르게 줄어든다"고 하면 사실과 어긋난다.
    # 20% 하락 시나리오가 여전히 안전 구간이면 그렇다고 말한다.
    drop_20 = (indicators.price_drop_scenarios or {}).get("drop_20")
    if drop_20 is None:
        tail = ""
    elif RiskRule.dtv_verdict(drop_20) == "SAFE":
        tail = (
            f" 매매가가 20% 하락해도 담보부담률은 {rate_text(drop_20)}로 "
            "안전 구간에 머물러 담보 여유는 넉넉합니다."
        )
    else:
        tail = (
            f" 매매가가 20% 하락하면 담보부담률이 {rate_text(drop_20)}까지 올라 "
            "여유가 빠르게 줄어듭니다."
        )

    shortfall = indicators.deposit_shortfall or 0
    if shortfall > 0:
        head = (
            f"선순위 채권을 뺀 회수 가능액은 {money(indicators.recoverable_amount)}에 그쳐 "
            f"현재 시세에서도 담보부담률이 "
            f"{rate_text(indicators.collateral_burden_rate)}입니다."
        )
    else:
        head = (
            f"선순위 채권을 뺀 회수 가능액은 {money(indicators.recoverable_amount)}으로 "
            f"보증금보다 {money(indicators.recoverable_amount - request.deposit)} 많고, "
            f"현재 시세 기준 담보부담률은 "
            f"{rate_text(indicators.collateral_burden_rate)}입니다."
        )

    return f"{head}{tail}"


def summary_reliability_text(reliability: ValuationReliability) -> str | None:
    if reliability == ValuationReliability.HIGH:
        return None

    return (
        f"다만 AI 시세 신뢰도가 {RELIABILITY_LABELS[reliability]}이라 "
        "추정 매매가 자체에 오차가 있을 수 있으니 인근 실거래가도 함께 확인해 주세요."
    )


def summary_text(
    request: DiagnosisRequest,
    result,
    reliability: ValuationReliability,
) -> str:
    grade_label = GRADE_LABELS[result.forced_warning.grade]
    final_score = result.forced_warning.score

    if final_score != result.risk_score.base_total:
        reason_codes = dict.fromkeys(
            (
                *result.risk_score.floor_reasons,
                *result.forced_warning.floor_reasons,
            )
        )
        causes = ", ".join(floor_reason_label(code) for code in reason_codes)
        lead = (
            f"기본 가중점수 {result.risk_score.base_total}점에 "
            f"{causes} 최종 판정 규칙을 반영해 "
            f"위험점수를 {final_score}점으로 조정했습니다. "
            f"최종 전세 위험등급은 {grade_label}입니다."
        )
    else:
        lead = (
            f"최종 위험점수 {final_score}점으로 "
            f"전세 위험등급은 {grade_label}입니다."
        )

    parts = [
        lead,
        headline_risk_text(request, result),
        summary_collateral_text(request, result),
        summary_reliability_text(reliability),
    ]
    return " ".join(part for part in parts if part)


def key_findings(
    request: DiagnosisRequest,
    result,
    reliability: ValuationReliability,
) -> list[ReportFinding]:
    indicators = result.risk_indicators
    deposit = request.deposit

    findings = [
        ReportFinding(
            title="보증금 대비 매매가",
            description=(
                f"계약 보증금 {money(deposit)}은 AI 예상 매매가 "
                f"{money(result.estimated_sale_price)}의 "
                f"{rate_text(indicators.lease_to_sale_rate)}입니다."
            ),
        ),
        lease_gap_finding(
            deposit,
            result.estimated_lease_price,
            indicators.lease_price_gap_rate,
        ),
    ]

    findings.extend(
        item
        for item in (
            collateral_finding(deposit, indicators),
            recovery_finding(deposit, indicators),
            reliability_finding(reliability, result),
            score_finding(request, result),
            score_floor_finding(result),
        )
        if item is not None
    )

    return findings


def risk_score_metrics(
    request: DiagnosisRequest,
    result,
) -> list[ReportMetric]:
    score = result.risk_score
    final_score = result.forced_warning.score
    price_label = (
        "담보 회수부담"
        if request.mode == DiagnosisMode.DETAILED
        else "계약가격 부담"
    )
    metrics = [
        ReportMetric(key="total", label="최종점수", value=final_score, unit="점"),
    ]
    if final_score != score.base_total:
        metrics.append(
            ReportMetric(
                key="base",
                label="기본 가중점수",
                value=score.base_total,
                unit="점",
            )
        )
    metrics.extend(
        [
            ReportMetric(
                key="priceBurden",
                label=price_label,
                value=score.price_burden,
                unit="점",
            ),
            ReportMetric(
                key="leaseMarketDeviation",
                label="주변 전세수준 이탈",
                value=score.lease_market_deviation,
                unit="점",
            ),
            ReportMetric(
                key="marketTrend",
                label="시장 추세",
                value=score.market_trend,
                unit="점",
            ),
        ]
    )
    if score.policy_adjustment:
        metrics.append(
            ReportMetric(
                key="policyAdjustment",
                label="가격 위험 하한 조정",
                value=score.policy_adjustment,
                unit="점",
            )
        )
    rights_adjustment = final_score - score.total
    if rights_adjustment:
        metrics.append(
            ReportMetric(
                key="rightsAdjustment",
                label="등기 권리 하한 조정",
                value=rights_adjustment,
                unit="점",
            )
        )
    return metrics


def build_report_detail(request: DiagnosisRequest, result, reliability) -> ReportDetail:
    indicators = result.risk_indicators
    registry = request.registry_risk
    final_grade = result.forced_warning.grade
    notices = [notice(code, registry) for code in result.forced_warning.warnings]
    notices.extend(
        missing_notice(code, registry) for code in result.missing_checks
    )

    sections = [
        ReportSection(
            key="valuation",
            title="시세 추정",
            description="입력 물건과 시장 데이터를 이용한 AI 추정 결과입니다.",
            metrics=[
                ReportMetric(key="salePrice", label="예상 매매가", value=result.estimated_sale_price, unit="원"),
                ReportMetric(key="leasePrice", label="예상 전세가", value=result.estimated_lease_price, unit="원"),
                ReportMetric(key="deposit", label="계약 보증금", value=request.deposit, unit="원"),
                ReportMetric(key="reliability", label="시세 신뢰도", value=reliability.value),
            ],
        )
    ]
    if request.mode == DiagnosisMode.DETAILED:
        sections.append(
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
            )
        )
    sections.append(
        ReportSection(
            key="riskScore",
            title="위험점수",
            description="기본 가중점수와 최종 판정 조정 내역입니다.",
            metrics=risk_score_metrics(request, result),
        )
    )

    scenarios = [
        price_scenario(key, burden_rate, result.estimated_sale_price)
        for key, burden_rate in (indicators.price_drop_scenarios or {}).items()
    ]
    actions = recommended_actions(request, result)

    return ReportDetail(
        title=(
            "간편 전세 위험도 진단 결과"
            if request.mode == DiagnosisMode.QUICK
            else "정밀 전세 위험도 진단 결과"
        ),
        gradeLabel=GRADE_LABELS[final_grade],
        sections=sections,
        notices=notices,
        priceScenarios=scenarios,
        explanation=ReportExplanation(
            summary=summary_text(request, result, reliability),
            keyFindings=key_findings(request, result, reliability),
            cautions=[item.description for item in notices],
            recommendedActions=actions,
            generatedBy="RULE",
        ),
    )


def percent(value: float | None) -> float | None:
    return round(value * 100, 2) if value is not None else None


def recommended_actions(
    request: DiagnosisRequest,
    result,
) -> list[ReportAction]:
    actions = []
    if request.mode == DiagnosisMode.QUICK:
        actions.append(
            ReportAction(
                label="정밀진단으로 추가 확인",
                description=(
                    "등기부등본을 첨부하는 정밀진단으로 근저당, 압류, "
                    "소유자 일치 여부를 추가 확인하세요."
                ),
            )
        )
    else:
        actions.append(
            ReportAction(
                label="등기부등본 재발급",
                description="계약 직전에 등기부등본을 다시 발급해 권리 변동을 확인하세요.",
            )
        )
        if result.forced_warning.warnings:
            actions.append(
                ReportAction(
                    label="계약 진행 보류",
                    description="확인된 등기 위험이 해소되기 전에는 계약 진행을 보류하세요.",
                )
            )
        if result.missing_checks:
            actions.append(
                ReportAction(
                    label="미확인 항목 확인",
                    description="미확인 항목을 확인한 뒤 최종 계약 여부를 결정하세요.",
                )
            )
    actions.append(
        ReportAction(
            label="보증보험 가입 확인",
            description="보증보험 가입 가능 여부와 예상 보증한도를 확인하세요.",
        )
    )
    return actions
