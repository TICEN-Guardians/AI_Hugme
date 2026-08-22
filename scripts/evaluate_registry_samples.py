import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ocr.registry_llm import extract_registry_pdf
from app.ocr.registry_merge import RegistryMergeError, merge_registry_results
from app.ocr.registry_pdf import load_registry_pdf
from app.ocr.registry_resolver import resolve_registry_extraction


def canonical(value):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", str(value or "")).lower()


def find_files(roots, samples):
    expected = {sample["filename"] for sample in samples}
    found = {}
    for root in roots:
        for path in root.rglob("*.pdf"):
            if path.name in expected and path.name not in found:
                found[path.name] = path
    missing = sorted(expected - found.keys())
    if missing:
        raise FileNotFoundError("찾지 못한 PDF: " + ", ".join(missing))
    return found


def owner_matches(expected, actual):
    actual_name = canonical(actual.get("name"))
    if not any(canonical(name) in actual_name or actual_name in canonical(name) for name in expected["names"]):
        return False
    expected_share = expected.get("share")
    return expected_share is None or canonical(expected_share) == canonical(actual.get("share"))


def compare_sample(expected, actual):
    checks = []

    def add(field, expected_value, actual_value, passed):
        checks.append({
            "field": field,
            "expected": expected_value,
            "actual": actual_value,
            "passed": bool(passed),
        })

    add("documentType", expected["documentType"], actual.get("document_type"), expected["documentType"] == actual.get("document_type"))
    address = actual.get("property_address") or ""
    missing_tokens = [token for token in expected["addressTokens"] if canonical(token) not in canonical(address)]
    add("address", expected["addressTokens"], address, not missing_tokens)
    if "exclusiveArea" in expected:
        actual_area = actual.get("exclusive_area")
        add("exclusiveArea", expected["exclusiveArea"], actual_area, actual_area is not None and abs(expected["exclusiveArea"] - actual_area) <= 0.001)

    actual_owners = actual.get("current_owners") or []
    unmatched = [owner for owner in expected["owners"] if not any(owner_matches(owner, item) for item in actual_owners)]
    add("owners", expected["owners"], [{"name": owner.get("name"), "share": owner.get("share")} for owner in actual_owners], not unmatched and len(actual_owners) == len(expected["owners"]))

    rights = actual.get("registry_rights") or {}
    add("activeMortgageCount", expected["activeMortgageCount"], rights.get("active_mortgage_count"), expected["activeMortgageCount"] == rights.get("active_mortgage_count"))
    add("totalActiveMaxClaimAmount", expected["totalActiveMaxClaimAmount"], rights.get("total_active_max_claim_amount"), expected["totalActiveMaxClaimAmount"] == rights.get("total_active_max_claim_amount"))
    active_jeonse = sorted(right.get("deposit_amount") for right in rights.get("jeonse_rights", []) if right.get("status") == "ACTIVE")
    add("activeJeonseAmounts", sorted(expected["activeJeonseAmounts"]), active_jeonse, sorted(expected["activeJeonseAmounts"]) == active_jeonse)
    add("parseStatus", "SUCCESS", actual.get("parse_status"), actual.get("parse_status") == "SUCCESS")
    add("sourceEvidence", "all rights have located raw text", None, all(bool(right.get("raw_text")) for right in rights.get("rights", [])))
    return checks


def compare_pair(expected, actual):
    rights = actual.get("registry_rights") or {}
    active_jeonse = sorted(right.get("deposit_amount") for right in rights.get("jeonse_rights", []) if right.get("status") == "ACTIVE")
    values = {
        "activeMortgageCount": rights.get("active_mortgage_count"),
        "totalActiveMaxClaimAmount": rights.get("total_active_max_claim_amount"),
        "activeJeonseAmounts": active_jeonse,
    }
    checks = []
    for field, actual_value in values.items():
        expected_value = sorted(expected[field]) if field == "activeJeonseAmounts" else expected[field]
        checks.append({"field": field, "expected": expected_value, "actual": actual_value, "passed": expected_value == actual_value})
    return checks


async def analyze_sample(sample, path, semaphore):
    async with semaphore:
        pdf_bytes = path.read_bytes()
        document = load_registry_pdf(pdf_bytes)
        extraction = await extract_registry_pdf(pdf_bytes, path.name, document.page_texts)
        result = resolve_registry_extraction(extraction, document.page_texts)
        checks = compare_sample(sample, result)
        return {
            "id": sample["id"],
            "filename": sample["filename"],
            "passed": all(check["passed"] for check in checks),
            "checks": checks,
            "result": result,
        }


async def run(args):
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    samples = fixture["samples"]
    files = find_files(args.source_root, samples)
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [analyze_sample(sample, files[sample["filename"]], semaphore) for sample in samples]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    reports = []
    resolved = {}
    for sample, result in zip(samples, results):
        if isinstance(result, Exception):
            reports.append({
                "id": sample["id"],
                "filename": sample["filename"],
                "passed": False,
                "error": f"{type(result).__name__}: {result}",
                "checks": [],
            })
        else:
            resolved[sample["id"]] = result.pop("result")
            reports.append(result)

    pair_reports = []
    sample_by_id = {sample["id"]: sample for sample in samples}
    for pair in fixture["pairs"]:
        try:
            pair_result = merge_registry_results(
                [resolved[sample_id] for sample_id in pair["sampleIds"]],
                [sample_by_id[sample_id]["filename"] for sample_id in pair["sampleIds"]],
            )
            checks = compare_pair(pair, pair_result)
            pair_reports.append({
                "id": pair["id"],
                "passed": all(check["passed"] for check in checks),
                "checks": checks,
            })
        except (KeyError, RegistryMergeError, ValueError) as error:
            pair_reports.append({
                "id": pair["id"],
                "passed": False,
                "error": f"{type(error).__name__}: {error}",
                "checks": [],
            })

    summary = {
        "sampleCount": len(reports),
        "samplePassed": sum(report["passed"] for report in reports),
        "pairCount": len(pair_reports),
        "pairPassed": sum(report["passed"] for report in pair_reports),
        "fieldChecks": sum(len(report["checks"]) for report in reports),
        "fieldChecksPassed": sum(check["passed"] for report in reports for check in report["checks"]),
    }
    output = {
        "evaluatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "samples": reports,
        "pairs": pair_reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    for report in reports:
        failed = [check["field"] for check in report["checks"] if not check["passed"]]
        suffix = report.get("error") or ", ".join(failed)
        print(f"{report['id']} {'PASS' if report['passed'] else 'FAIL'} {suffix}".rstrip())
    for report in pair_reports:
        failed = [check["field"] for check in report["checks"] if not check["passed"]]
        suffix = report.get("error") or ", ".join(failed)
        print(f"{report['id']} {'PASS' if report['passed'] else 'FAIL'} {suffix}".rstrip())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=Path("tests/fixtures/registry_samples.json"))
    parser.add_argument("--source-root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
