import logging
import os

from openai import OpenAI
from pydantic import BaseModel

from app.diagnosis.schemas import ReportDetail, ReportExplanation


logger = logging.getLogger(__name__)


class LlmExplanation(BaseModel):
    summary: str
    key_findings: list[str]
    cautions: list[str]
    recommended_actions: list[str]


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
                "법률적 확정 표현을 피하고 JSON만 반환한다."
            ),
            input=(
                "다음 규칙 기반 리포트를 설명하라. "
                "summary는 2문장 이내, 각 배열은 최대 4개로 작성한다. "
                "제공된 응답 스키마의 필드만 작성한다.\n"
                + report.model_dump_json(by_alias=True, exclude={"explanation"})
            ),
            text_format=LlmExplanation,
            store=False,
        )
        payload = response.output_parsed
        if payload is None:
            raise RuntimeError("LLM 설명 구조화 결과 없음")
        explanation = ReportExplanation(
            summary=payload.summary,
            keyFindings=payload.key_findings,
            cautions=payload.cautions,
            recommendedActions=payload.recommended_actions,
            generatedBy="LLM",
        )
        return report.model_copy(update={"explanation": explanation})
    except Exception:
        logger.exception("진단 LLM 설명 생성 실패, 규칙 리포트 반환")
        return report
