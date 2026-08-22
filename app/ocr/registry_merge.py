import re


class RegistryMergeError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _canonical(value: str | None) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", value or "").lower()


def _source_filename(value: str) -> str:
    return re.sub(r"[\[\]\r\n]+", "_", value).strip() or "unnamed.pdf"


def _owner_identity(owner: dict) -> tuple[str, str, str]:
    return (
        _canonical(owner.get("name")),
        re.sub(r"\D", "", owner.get("jumin_front") or ""),
        _canonical(owner.get("share")),
    )


def _merge_flag(values: list[str]) -> str:
    if "TRUE" in values:
        return "TRUE"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    return "FALSE"


def _merge_section_status(values: list[str], *, eul: bool = False) -> str:
    if "PARSE_FAILED" in values:
        return "PARSE_FAILED"
    if eul and values and all(value == "CONFIRMED_NONE" for value in values):
        return "CONFIRMED_NONE"
    return "EXTRACTED"


def _party_key(value: str | None) -> str:
    without_registration_number = re.sub(
        r"\b\d{6}-\d{7}\b",
        "",
        value or "",
    )
    return _canonical(without_registration_number)


def _claim_signatures(claim: dict, allow_party_match: bool) -> set[tuple]:
    amount = claim.get("max_claim_amount")
    status = claim.get("status")
    registered_at = claim.get("registered_at")
    receipt_no = _canonical(claim.get("receipt_no"))
    creditor = _party_key(claim.get("creditor"))
    debtor = _party_key(claim.get("debtor"))
    signatures: set[tuple] = set()
    if amount is not None and receipt_no and registered_at:
        signatures.add(("RECEIPT", registered_at, receipt_no, amount, status))
    if allow_party_match and amount is not None and creditor and debtor:
        signatures.add(("PARTIES", creditor, debtor, amount, status))
    if allow_party_match:
        for registered_at, receipt_no, amended_amount in claim.get("_link_signatures", []):
            linked_amount = amended_amount if amended_amount is not None else amount
            if registered_at and receipt_no and linked_amount is not None:
                signatures.add((
                    "AMENDMENT", registered_at, receipt_no, linked_amount, status
                ))
    return signatures


def _deposit_signatures(right: dict) -> set[tuple]:
    amount = right.get("deposit_amount")
    registered_at = right.get("registered_at")
    holder = _party_key(right.get("holder"))
    receipt_no = _canonical(right.get("receipt_no"))
    status = right.get("status")
    signatures: set[tuple] = set()
    if amount is not None and receipt_no and registered_at:
        signatures.add(("RECEIPT", registered_at, receipt_no, amount, status))
    if amount is not None and registered_at and holder:
        signatures.add(("PARTY", registered_at, holder, amount, status))
    return signatures


def _dedupe_cross_document(
    groups: list[list[dict]],
    signatures,
) -> list[dict]:
    merged: list[dict] = []
    seen_signatures: set[tuple] = set()
    for document_index, items in enumerate(groups):
        for item in items:
            item_signatures = signatures(item)
            if document_index > 0 and item_signatures & seen_signatures:
                continue
            merged.append(item)
            seen_signatures.update(item_signatures)
    return merged


def _document_priority(result: dict) -> int:
    return {
        "CONDOMINIUM": 3,
        "BUILDING": 2,
        "LAND": 1,
    }.get(result.get("document_type"), 0)


def merge_registry_results(results: list[dict], filenames: list[str]) -> dict:
    if len(results) != len(filenames) or not results:
        raise ValueError("병합할 등기 결과와 파일명이 일치하지 않습니다.")
    if len(results) == 1:
        single = dict(results[0])
        single_rights = dict(single["registry_rights"])
        single_rights["rights"] = [
            {
                **right,
                "raw_text": f"[FILE {_source_filename(filenames[0])}] {right['raw_text']}",
            }
            for right in single_rights["rights"]
        ]
        single["registry_rights"] = single_rights
        return single

    addresses = {_canonical(result.get("property_address")) for result in results}
    if "" in addresses or len(addresses) != 1:
        raise RegistryMergeError(
            "REGISTRY_PROPERTY_MISMATCH",
            "서로 다른 부동산의 등기부입니다. 같은 주소의 토지·건물 등기부만 함께 업로드해 주세요.",
        )

    document_types = {result.get("document_type") for result in results}
    if document_types != {"LAND", "BUILDING"}:
        raise RegistryMergeError(
            "REGISTRY_DOCUMENT_SET_INVALID",
            "두 파일 업로드는 같은 부동산의 토지 등기부와 건물 등기부 조합만 지원합니다.",
        )

    owner_sets = [
        {_owner_identity(owner) for owner in result["current_owners"]}
        for result in results
    ]
    if not owner_sets[0] or any(owner_set != owner_sets[0] for owner_set in owner_sets[1:]):
        raise RegistryMergeError(
            "REGISTRY_OWNER_MISMATCH",
            "토지와 건물 등기부의 현재 소유자가 일치하지 않아 자동 병합할 수 없습니다.",
        )

    primary = max(results, key=_document_priority)
    merged = dict(primary)
    rights_by_document = [result["registry_rights"] for result in results]
    allow_party_match = all(
        result.get("has_joint_collateral_mention", False)
        for result in results
    )

    public_rights = []
    for filename, rights in zip(filenames, rights_by_document):
        for right in rights["rights"]:
            copied = dict(right)
            copied["raw_text"] = f"[FILE {_source_filename(filename)}] {right['raw_text']}"
            public_rights.append(copied)

    mortgage_groups = []
    for rights in rights_by_document:
        link_signatures = rights.get("mortgage_link_signatures", {})
        mortgage_groups.append([
            {
                **mortgage,
                "_link_signatures": link_signatures.get(mortgage["rank_no"], []),
            }
            for mortgage in rights["mortgages"]
        ])
    mortgages = _dedupe_cross_document(
        mortgage_groups,
        lambda claim: _claim_signatures(claim, allow_party_match),
    )
    mortgages = [
        {key: value for key, value in claim.items() if key != "_link_signatures"}
        for claim in mortgages
    ]
    jeonse_rights = _dedupe_cross_document(
        [rights["jeonse_rights"] for rights in rights_by_document],
        _deposit_signatures,
    )
    leaseholds = _dedupe_cross_document(
        [rights["leasehold_registrations"] for rights in rights_by_document],
        _deposit_signatures,
    )
    active_mortgages = [
        mortgage for mortgage in mortgages if mortgage["status"] == "ACTIVE"
    ]
    active_amounts = [mortgage["max_claim_amount"] for mortgage in active_mortgages]
    total_mortgage = (
        None if any(amount is None for amount in active_amounts)
        else sum(active_amounts)
    )

    flag_names = rights_by_document[0]["flags"].keys()
    flags = {
        flag: _merge_flag([rights["flags"][flag] for rights in rights_by_document])
        for flag in flag_names
    }
    merged["registry_rights"] = {
        "gap_section_status": _merge_section_status([
            rights["gap_section_status"] for rights in rights_by_document
        ]),
        "eul_section_status": _merge_section_status([
            rights["eul_section_status"] for rights in rights_by_document
        ], eul=True),
        "rights": public_rights,
        "mortgages": mortgages,
        "jeonse_rights": jeonse_rights,
        "leasehold_registrations": leaseholds,
        "flags": flags,
        "active_mortgage_count": len(active_mortgages),
        "total_active_max_claim_amount": total_mortgage,
        "llm_right_count": sum(
            rights["llm_right_count"] for rights in rights_by_document
        ),
        "verified_right_count": sum(
            rights["verified_right_count"] for rights in rights_by_document
        ),
    }
    issue_dates = [result["issue_date"] for result in results if result.get("issue_date")]
    merged["issue_date"] = min(issue_dates) if issue_dates else None
    merged["has_cancellation_mention"] = any(
        result["has_cancellation_mention"] for result in results
    )

    status_priority = {"SUCCESS": 0, "NEEDS_REVIEW": 1, "PARTIAL": 2, "FAILED": 3}
    confidence_priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}
    merged["parse_status"] = max(
        (result["parse_status"] for result in results),
        key=status_priority.get,
    )
    merged["parse_confidence"] = max(
        (result["parse_confidence"] for result in results),
        key=confidence_priority.get,
    )
    if total_mortgage is None and merged["parse_status"] == "SUCCESS":
        merged["parse_status"] = "NEEDS_REVIEW"
        merged["parse_confidence"] = "MEDIUM"
    return merged
