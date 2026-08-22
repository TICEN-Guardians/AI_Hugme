"""
등기부등본 OCR + HUG 악성임대인 명단 대조 라우터.

main.py에서는 아래처럼 include만 하면 됨:

    from app.ocr.router import router as ocr_router
    app.include_router(ocr_router, prefix="/register", tags=["ocr"])
"""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.ocr.registry_pdf import RegistryPdfError, load_registry_pdf
from app.ocr.registry_llm import extract_registry_pdf
from app.ocr.registry_resolver import resolve_registry_extraction
from app.ocr.registry_merge import RegistryMergeError, merge_registry_results
from app.ocr.matcher import find_bad_landlord_matches
from app.ocr.registry_repository import save_registry_result, save_watchlist_checks
from app.ocr.schemas import (
    CurrentOwner,
    OcrRegisterResponse,
    OwnerMatchResult,
    RegisterCheckResponse,
    RegistrySummary,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_STATUS_PRIORITY = {"MATCH_HIGH": 3, "MATCH_NAME_ONLY": 2, "UNKNOWN": 1, "NO_MATCH": 0}


@router.post("/ocr", response_model=OcrRegisterResponse)
async def analyze_register(
    files: list[UploadFile] = File(...),
    analysis_id: str = Form(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="파일이 없습니다.")

    if len(files) > 2:
        raise HTTPException(
            status_code=400,
            detail="등기부 PDF는 집합건물 1개 또는 같은 주소의 토지·건물 2개까지 업로드할 수 있습니다.",
        )

    uploaded_documents = []
    for uploaded in files:
        filename = (uploaded.filename or "").lower()
        content_type = (uploaded.content_type or "").lower()
        if content_type != "application/pdf" and not filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="등기부등본은 PDF 파일만 업로드할 수 있습니다.",
            )

        content = await uploaded.read()
        try:
            registry_document = load_registry_pdf(content)
        except RegistryPdfError as exc:
            client_error_codes = {
                "EMPTY_FILE",
                "FILE_TOO_LARGE",
                "NOT_PDF",
                "BROKEN_PDF",
                "PASSWORD_PROTECTED",
                "INVALID_PAGE_COUNT",
            }
            status_code = 400 if exc.code in client_error_codes else 422
            raise HTTPException(
                status_code=status_code,
                detail={
                    "code": exc.code,
                    "message": f"{uploaded.filename or 'registry.pdf'}: {exc}",
                },
            ) from exc
        uploaded_documents.append((uploaded, content, registry_document))

    try:
        extractions = await asyncio.gather(*[
            extract_registry_pdf(
                content,
                uploaded.filename or "registry.pdf",
                registry_document.page_texts,
            )
            for uploaded, content, registry_document in uploaded_documents
        ])
        resolved_results = [
            resolve_registry_extraction(extracted, registry_document.page_texts)
            for extracted, (_, _, registry_document)
            in zip(extractions, uploaded_documents)
        ]
    except Exception as exc:
        missing_api_key = "OPENAI_API_KEY" in str(exc)
        logger.exception("등기부 LLM 구조화 실패 (analysis_id=%s)", analysis_id)
        raise HTTPException(
            status_code=503 if missing_api_key else 502,
            detail={
                "code": (
                    "REGISTRY_EXTRACTION_NOT_CONFIGURED"
                    if missing_api_key
                    else "REGISTRY_EXTRACTION_FAILED"
                ),
                "message": (
                    "등기부 분석 서비스 설정이 완료되지 않았습니다."
                    if missing_api_key
                    else "등기부 내용을 구조화하지 못했습니다. 잠시 후 다시 시도해 주세요."
                ),
            },
        ) from exc

    filenames = [
        uploaded.filename or "registry.pdf"
        for uploaded, _, _ in uploaded_documents
    ]
    try:
        fields = merge_registry_results(resolved_results, filenames)
    except RegistryMergeError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    text = "\n\n".join(
        f"[FILE {filename}]\n{registry_document.text}"
        for filename, (_, _, registry_document)
        in zip(filenames, uploaded_documents)
    )
    rights = fields["registry_rights"]

    return OcrRegisterResponse(
        analysis_id=analysis_id,
        parse_status=fields["parse_status"],
        parse_confidence=fields["parse_confidence"],
        parsed_at=datetime.now(timezone.utc).isoformat(),
        raw_address=fields["property_address"],
        property_address=fields["property_address"],
        dong_name=fields["dong_name"],
        floor=fields["floor"],
        ho_name=fields["ho_name"],
        exclusive_area=fields["exclusive_area"],
        issue_date=fields["issue_date"],
        current_owners=[CurrentOwner(**o) for o in fields["current_owners"]],
        ownership_history=fields["ownership_history"],
        rights=rights["rights"],
        mortgages=rights["mortgages"],
        jeonse_rights=rights["jeonse_rights"],
        leasehold_registrations=rights["leasehold_registrations"],
        summary=RegistrySummary(
            gap_section_status=rights["gap_section_status"],
            eul_section_status=rights["eul_section_status"],
            active_mortgage_count=rights["active_mortgage_count"],
            total_active_max_claim_amount=rights["total_active_max_claim_amount"],
            **{
                ("has_active_leasehold_registration" if k == "has_leasehold_registration" else k): v
                for k, v in rights["flags"].items()
            },
        ),
        has_cancellation_mention=fields["has_cancellation_mention"],
        raw_text=text,
        source_type="pdf_llm",
    )


@router.post("/check", response_model=RegisterCheckResponse)
async def register_check(
    files: list[UploadFile] = File(...),
    analysis_id: str = Form(...),
):
    """
    등기부등본 업로드 -> OCR/파싱(권리 포함) -> 최종 소유자(들)를 bad_landlord 명단과
    대조까지 한 번에 처리. 위험도 진단 흐름에서 실제로 쓰는 엔드포인트.
    """
    ocr_result = await analyze_register(files=files, analysis_id=analysis_id)

    results = []

    if not ocr_result.current_owners:
        # 등본 파싱 실패 등으로 소유자를 하나도 못 뽑은 경우
        results.append(
            OwnerMatchResult(
                owner=None,
                check_status="NOT_CHECKED",
                matched=None,
                match_type=None,
                match_status="UNKNOWN",
                match_candidates=[],
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        )

    for owner in ocr_result.current_owners:
        checked_at = datetime.now(timezone.utc).isoformat()
        try:
            match = find_bad_landlord_matches(
                name=owner.name,
                jumin_front=owner.jumin_front,
            )
            status = match.status
            candidates = match.candidates
            check_status = "CHECKED"
        except Exception:
            logger.exception(
                "악성임대인 조회 실패 (analysis_id=%s)",
                analysis_id,
            )
            status = "UNKNOWN"
            candidates = []
            check_status = "ERROR"

        matched: bool | None
        match_type: str | None
        if status == "MATCH_HIGH":
            matched, match_type = True, "EXACT"
        elif status == "MATCH_NAME_ONLY":
            matched, match_type = None, "MANUAL_REVIEW"
        elif status == "NO_MATCH":
            matched, match_type = False, None
        else:  # UNKNOWN
            matched, match_type = None, None

        results.append(
            OwnerMatchResult(
                owner=owner,
                check_status=check_status,
                matched=matched,
                match_type=match_type,
                match_status=status,
                match_candidates=candidates,
                checked_at=checked_at,
            )
        )

    overall = "UNKNOWN" if not ocr_result.current_owners else "NO_MATCH"
    for r in results:
        if _STATUS_PRIORITY.get(r.match_status, 0) > _STATUS_PRIORITY[overall]:
            overall = r.match_status

    response = RegisterCheckResponse(
        owner_info=ocr_result,
        results=results,
        overall_match_status=overall,
    )

    # DB 저장
    # 저장에 실패하면 위험도 진단이 등기 권리관계를 통째로 빠뜨린 채 수행되므로
    # 성공으로 응답하지 않는다.
    try:
        registry_result_id, owner_ids = save_registry_result(analysis_id, ocr_result)
        save_watchlist_checks(analysis_id, registry_result_id, owner_ids, response)
    except Exception as e:
        logger.exception("registry 저장 실패 (analysis_id=%s): %s", analysis_id, e)
        raise HTTPException(
            status_code=500,
            detail="등기부등본 분석 결과를 저장하지 못했습니다. 다시 시도해 주세요.",
        ) from e

    return response
