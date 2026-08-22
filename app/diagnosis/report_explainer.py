import logging
import os

from openai import OpenAI
from pydantic import BaseModel

from app.diagnosis.schemas import ReportAction, ReportDetail, ReportExplanation


logger = logging.getLogger(__name__)


class LlmAction(BaseModel):
    label: str
    description: str


class LlmExplanation(BaseModel):
    """LLM은 요약과 행동 권고 문장만 다시 쓴다.

    keyFindings·cautions는 수치와 등기 사실을 그대로 담아야 해서
    규칙 기반으로 만든 문장을 그대로 사용한다.
    """

    summary: str
    recommended_actions: list[LlmAction]


def keeps_forced_cause(summary: str, report: ReportDetail) -> bool:
    """등급을 끌어올린 등기 위험을 LLM 요약이 빠뜨렸는지 확인한다.

    점수만 남고 사유가 사라지면 '38점인데 왜 매우 높음인가'가 설명되지 않아
    규칙 요약으로 되돌린다.
    """
    causes = [item.title for item in report.notices if item.severity != "INFO"]
    if not causes:
        return True

    return any(
        any(token and token in summary for token in title.split())
        for title in causes
    )


def explain_report(report: ReportDetail) -> ReportDetail:
    if os.getenv("DIAGNOSIS_LLM_ENABLED", "true").lower() != "true":
        return report

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return report

    try:
        client = OpenAI(
            api_key=api_key,
            timeout=float(os.getenv("DIAGNOSIS_LLM_TIMEOUT", "30")),
        )
        response = client.responses.parse(
            model=os.getenv("DIAGNOSIS_LLM_MODEL", "gpt-4o-mini"),
            instructions=(
                "전세 위험도 진단 결과를 한국어로 설명한다. "
                "숫자, 등급, 경고를 변경하거나 새로운 사실을 만들지 않는다. "
                "리포트에 없는 수치는 쓰지 않고, 법률적 확정 표현을 피하며 JSON만 반환한다. "
                "리포트에 적혀 있지 않은 인과관계를 만들지 않는다. "
                "'이로 인해', '따라서', '그 결과' 같은 접속으로 서로 다른 항목을 "
                "원인과 결과로 잇지 않는다. "
                "리포트가 위험이 낮다고 적은 항목을 위험한 것처럼 바꿔 쓰지 않는다."
            ),
            input=(
                "다음 규칙 기반 리포트의 summary와 recommended_actions만 다시 쓴다. "
                "summary는 3~5문장으로, 등급 판단 근거와 주요 위험요인을 리포트에 있는 "
                "구체적인 수치·사실과 함께 순서대로 설명한다. "
                "기존 summary가 담고 있는 사실은 빼지 말고 문장만 자연스럽게 다듬는다. "
                "특히 위험점수와 최종 등급이 다른 이유는 반드시 유지한다. "
                "recommended_actions는 최대 4개이며, 각 항목의 description은 계약자가 "
                "바로 실행할 수 있는 행동 문장으로, label은 그 행동을 12자 이내 "
                "명사형으로 줄인 말(서술어·조사 없이)로 쓴다. "
                "제공된 응답 스키마의 필드만 작성한다.\n"
                + report.model_dump_json(by_alias=True)
            ),
            text_format=LlmExplanation,
            store=False,
        )
        payload = response.output_parsed
        if payload is None:
            raise RuntimeError("LLM 설명 구조화 결과 없음")
        rule_explanation = report.explanation
        explanation = ReportExplanation(
            summary=(
                payload.summary
                if keeps_forced_cause(payload.summary, report)
                else rule_explanation.summary
            ),
            keyFindings=rule_explanation.key_findings,
            cautions=rule_explanation.cautions,
            recommendedActions=(
                [
                    ReportAction(
                        label=action.label.strip() or action.description,
                        description=action.description,
                    )
                    for action in payload.recommended_actions
                    if action.description.strip()
                ]
                or rule_explanation.recommended_actions
            ),
            generatedBy="RULE_LLM",
        )
        return report.model_copy(update={"explanation": explanation})
    except Exception:
        logger.exception("진단 LLM 설명 생성 실패, 규칙 리포트 반환")
        return report
