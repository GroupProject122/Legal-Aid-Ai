from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from config import BASE_DIR, DOCUMENTS_DIR
from ingest import CORPUS_MANIFEST_PATH

PARSED_DIR = BASE_DIR / "parsed"
LEGAL_CHUNKS_PATH = PARSED_DIR / "legal_chunks.jsonl"
AUDIT_JSON_PATH = PARSED_DIR / "ingestion_audit.json"
AUDIT_MD_PATH = PARSED_DIR / "ingestion_audit.md"

MANIFEST_FIELDS = (
    "domain",
    "jurisdiction",
    "document_title",
    "document_type",
    "status",
    "authority_level",
    "year",
    "retrieval_priority",
)
NUMBER_FIELD_BY_STRUCTURE = {
    "section": "section_number",
    "article": "article_number",
    "rule": "rule_number",
    "regulation": "regulation_number",
}
TITLE_OR_NUMBER_STRUCTURES = {
    "guideline": ("guideline_number", "guideline_title", "provision_number", "provision_title"),
    "manual_section": ("heading_number", "heading_title", "provision_number", "provision_title"),
}
NEUTRAL_STRUCTURES = {"preamble", "schedule", "annexure", "heading", "fallback"}
STRUCTURE_AWARE_TYPES = {
    "section",
    "article",
    "rule",
    "regulation",
    "guideline",
    "manual_section",
    "preamble",
    "schedule",
    "annexure",
    "heading",
}


def load_jsonl(path: Path = LEGAL_CHUNKS_PATH) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
            record["_line_number"] = line_number
            records.append(record)
    return records


def load_manifest(path: Path = CORPUS_MANIFEST_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return {
        entry.get("source_file"): entry
        for entry in manifest.get("documents", [])
        if entry.get("source_file")
    }


def add_issue(
    issues: list[dict[str, Any]],
    severity: str,
    issue_type: str,
    message: str,
    record: dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    item = {"severity": severity, "type": issue_type, "message": message}
    if record:
        item.update(
            {
                "chunk_id": record.get("chunk_id"),
                "source_file": record.get("source_file"),
                "line_number": record.get("_line_number"),
            }
        )
    item.update(extra)
    issues.append(item)


def provision_identity(record: dict[str, Any]) -> str | None:
    structure_type = record.get("structure_type")
    if structure_type == "section":
        return f"section:{record.get('section_number')}"
    if structure_type == "article":
        return f"article:{record.get('article_number')}"
    if structure_type == "rule":
        return f"rule:{record.get('rule_number')}"
    if structure_type == "regulation":
        return f"regulation:{record.get('regulation_number')}"
    if structure_type == "guideline":
        return f"guideline:{record.get('guideline_number') or record.get('provision_number')}"
    if structure_type == "manual_section":
        return f"manual_section:{record.get('heading_number') or record.get('provision_number')}"
    if structure_type in {"schedule", "annexure", "preamble", "heading"}:
        return f"{structure_type}:{record.get('provision_title') or record.get('heading_title')}"
    return None


def validate_basic_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    chunk_id_counts = Counter(record.get("chunk_id") for record in records)
    for chunk_id, count in chunk_id_counts.items():
        if not chunk_id:
            continue
        if count > 1:
            add_issue(
                issues,
                "HIGH",
                "duplicate_chunk_id",
                f"chunk_id appears {count} times",
                chunk_id=chunk_id,
                count=count,
            )

    required = ("chunk_id", "text", "source_file", "document_title", "domain", "document_type", "structure_type")
    for record in records:
        for field in required:
            if not str(record.get(field) or "").strip():
                add_issue(issues, "HIGH", f"missing_{field}", f"Missing required field: {field}", record)
        page_start = record.get("page_start")
        page_end = record.get("page_end")
        page = record.get("page")
        for field, value in (("page", page), ("page_start", page_start), ("page_end", page_end)):
            if value is not None and (not isinstance(value, int) or value <= 0):
                add_issue(issues, "HIGH", "invalid_page_metadata", f"Invalid {field}: {value}", record)
        if isinstance(page_start, int) and isinstance(page_end, int) and page_start > page_end:
            add_issue(issues, "HIGH", "invalid_page_range", "page_start is greater than page_end", record)
    return issues


def validate_provision_metadata(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for record in records:
        structure_type = record.get("structure_type")
        number_field = NUMBER_FIELD_BY_STRUCTURE.get(structure_type)
        if number_field and not record.get(number_field):
            add_issue(
                issues,
                "MEDIUM",
                "missing_provision_number",
                f"{structure_type} chunk is missing {number_field}",
                record,
            )
        elif structure_type in TITLE_OR_NUMBER_STRUCTURES:
            fields = TITLE_OR_NUMBER_STRUCTURES[structure_type]
            if not any(record.get(field) for field in fields):
                add_issue(
                    issues,
                    "LOW",
                    "missing_provision_identifier",
                    f"{structure_type} chunk has no clear number or title",
                    record,
                )
        elif structure_type not in NUMBER_FIELD_BY_STRUCTURE and structure_type not in NEUTRAL_STRUCTURES:
            add_issue(issues, "LOW", "unknown_structure_type", f"Unknown structure_type: {structure_type}", record)
    return issues


def text_snippet(text: str, limit: int = 160) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def short_chunk_findings(records: list[dict[str, Any]]) -> dict[str, Any]:
    very_short = []
    review = []
    for record in records:
        length = len(record.get("text") or "")
        item = {
            "chunk_id": record.get("chunk_id"),
            "source_file": record.get("source_file"),
            "structure_type": record.get("structure_type"),
            "char_count": length,
            "snippet": text_snippet(record.get("text") or ""),
        }
        if length < 40:
            very_short.append(item)
        elif length < 100:
            review.append(item)
    return {
        "very_suspicious_under_40_count": len(very_short),
        "review_40_to_100_count": len(review),
        "very_suspicious_samples": very_short[:30],
        "review_samples": review[:30],
        "counts_by_source": dict(Counter(item["source_file"] for item in very_short + review)),
    }


def large_chunk_findings(records: list[dict[str, Any]]) -> dict[str, Any]:
    large = []
    high = []
    top = []
    for record in records:
        length = len(record.get("text") or "")
        number = (
            record.get("section_number")
            or record.get("article_number")
            or record.get("rule_number")
            or record.get("regulation_number")
            or record.get("guideline_number")
            or record.get("provision_number")
        )
        item = {
            "chunk_id": record.get("chunk_id"),
            "source_file": record.get("source_file"),
            "structure_type": record.get("structure_type"),
            "provision_number": number,
            "char_count": length,
        }
        top.append(item)
        if length > 15000:
            high.append(item)
        elif length > 8000:
            large.append(item)
    top.sort(key=lambda item: item["char_count"], reverse=True)
    return {
        "review_over_8000_count": len(large),
        "high_priority_over_15000_count": len(high),
        "review_over_8000": large[:50],
        "high_priority_over_15000": high[:50],
        "top_20_largest": top[:20],
    }


def normalize_for_duplicate(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def duplicate_findings(records: list[dict[str, Any]]) -> dict[str, Any]:
    exact_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    near_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        normalized = normalize_for_duplicate(record.get("text") or "")
        if not normalized:
            continue
        exact_groups[normalized].append(record)
        tokens = normalized.split()
        if len(tokens) >= 30:
            signature = " ".join(tokens[:40])
            near_buckets[signature].append(record)

    exact = [
        {
            "count": len(group),
            "chunk_ids": [record.get("chunk_id") for record in group[:20]],
            "source_files": sorted({record.get("source_file") for record in group}),
            "snippet": text_snippet(group[0].get("text") or ""),
        }
        for group in exact_groups.values()
        if len(group) > 1
    ]
    near = [
        {
            "count": len(group),
            "chunk_ids": [record.get("chunk_id") for record in group[:20]],
            "source_files": sorted({record.get("source_file") for record in group}),
            "snippet": text_snippet(group[0].get("text") or ""),
        }
        for group in near_buckets.values()
        if len(group) > 1
    ]
    exact.sort(key=lambda item: item["count"], reverse=True)
    near.sort(key=lambda item: item["count"], reverse=True)
    return {
        "exact_duplicate_group_count": len(exact),
        "near_duplicate_group_count": len(near),
        "exact_duplicate_groups": exact[:50],
        "near_duplicate_groups": near[:50],
    }


def header_footer_noise_findings(records: list[dict[str, Any]]) -> dict[str, Any]:
    line_sources: dict[str, set[str]] = defaultdict(set)
    line_counts: Counter[str] = Counter()
    noisy_patterns = (
        "regd. no.",
        "extraordinary",
        "gazette",
        "cg-dl",
        "ministry of",
        "downloaded from",
        "published by authority",
        "पंजीकरण",
        "असाधारण",
    )
    for record in records:
        source = record.get("source_file")
        for line in (record.get("text") or "").splitlines():
            normalized = re.sub(r"\s+", " ", line).strip()
            if len(normalized) < 8 or len(normalized) > 180:
                continue
            lowered = normalized.lower()
            if any(pattern in lowered for pattern in noisy_patterns) or len(line_sources[normalized]) >= 2:
                line_counts[normalized] += 1
                line_sources[normalized].add(source)

    repeated = [
        {
            "text": line,
            "count": count,
            "source_files": sorted(line_sources[line])[:20],
            "source_file_count": len(line_sources[line]),
        }
        for line, count in line_counts.most_common(50)
        if count >= 3 or len(line_sources[line]) >= 2
    ]
    return {
        "suspicious_pattern_count": len(repeated),
        "patterns": repeated,
    }


def parse_number_for_sequence(value: Any) -> tuple[int, str] | None:
    if not value:
        return None
    match = re.match(r"^(\d{1,4})([A-Z]?)", str(value))
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def sequence_anomalies(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    field_by_type = {
        "section": "section_number",
        "article": "article_number",
        "rule": "rule_number",
        "regulation": "regulation_number",
    }
    anomalies = []
    by_document_type: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        structure_type = record.get("structure_type")
        if structure_type in field_by_type:
            by_document_type[(record.get("source_file"), structure_type)].append(record)

    for (source_file, structure_type), group in by_document_type.items():
        seen_order: list[tuple[int, str, dict[str, Any]]] = []
        last_identity = None
        for record in group:
            identity = provision_identity(record)
            if identity == last_identity:
                continue
            last_identity = identity
            parsed = parse_number_for_sequence(record.get(field_by_type[structure_type]))
            if parsed:
                seen_order.append((parsed[0], parsed[1], record))
        for previous, current in zip(seen_order, seen_order[1:]):
            prev_num = previous[0]
            current_num = current[0]
            if current_num + 10 < prev_num:
                anomalies.append(
                    {
                        "severity": "MEDIUM",
                        "type": "sequence_reverse_jump",
                        "source_file": source_file,
                        "structure_type": structure_type,
                        "previous_chunk_id": previous[2].get("chunk_id"),
                        "current_chunk_id": current[2].get("chunk_id"),
                        "previous_number": previous[2].get(field_by_type[structure_type]),
                        "current_number": current[2].get(field_by_type[structure_type]),
                    }
                )
    return anomalies


def child_chunk_issues(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        count = record.get("provision_chunk_count")
        if isinstance(count, int) and count > 1:
            key = (
                record.get("source_file"),
                record.get("structure_type"),
                provision_identity(record),
                record.get("page_start"),
                record.get("page_end"),
            )
            grouped[key].append(record)
    manifest_fields = ("domain", "jurisdiction", "document_title", "document_type", "status", "authority_level", "year")
    for key, group in grouped.items():
        expected_count = group[0].get("provision_chunk_count")
        indices = sorted(record.get("provision_chunk_index") for record in group)
        expected_indices = list(range(1, expected_count + 1))
        if len(group) != expected_count or indices != expected_indices:
            issues.append(
                {
                    "severity": "HIGH",
                    "type": "invalid_child_chunk_sequence",
                    "source_file": key[0],
                    "provision": key[2],
                    "expected_count": expected_count,
                    "actual_count": len(group),
                    "indices": indices,
                    "chunk_ids": [record.get("chunk_id") for record in group],
                }
            )
        baseline = {field: group[0].get(field) for field in manifest_fields}
        for record in group[1:]:
            mismatches = [field for field in manifest_fields if record.get(field) != baseline[field]]
            if mismatches:
                issues.append(
                    {
                        "severity": "HIGH",
                        "type": "child_chunk_manifest_mismatch",
                        "source_file": key[0],
                        "provision": key[2],
                        "chunk_id": record.get("chunk_id"),
                        "fields": mismatches,
                    }
                )
    return issues


def page_range_issues(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    for record in records:
        page_start = record.get("page_start")
        page_end = record.get("page_end")
        if isinstance(page_start, int) and isinstance(page_end, int) and page_end - page_start > 50:
            add_issue(
                issues,
                "MEDIUM",
                "large_page_range",
                "Chunk spans more than 50 pages",
                record,
                page_start=page_start,
                page_end=page_end,
            )
    return issues


def fallback_statistics(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_document: dict[str, dict[str, Any]] = {}
    for record in records:
        source = record.get("source_file")
        stats = by_document.setdefault(
            source,
            {
                "source_file": source,
                "domain": record.get("domain"),
                "document_type": record.get("document_type"),
                "total_chunks": 0,
                "fallback_chunks": 0,
            },
        )
        stats["total_chunks"] += 1
        if record.get("structure_type") == "fallback":
            stats["fallback_chunks"] += 1
    for stats in by_document.values():
        total = stats["total_chunks"] or 1
        fallback = stats["fallback_chunks"]
        stats["structure_aware_chunks"] = stats["total_chunks"] - fallback
        stats["fallback_percentage"] = round(fallback / total * 100, 2)
        stats["structure_aware_percentage"] = round(stats["structure_aware_chunks"] / total * 100, 2)
    ranked = sorted(by_document.values(), key=lambda item: item["fallback_percentage"], reverse=True)
    return {
        "total_fallback_chunks": sum(item["fallback_chunks"] for item in by_document.values()),
        "by_document_ranked": ranked,
    }


def structure_coverage(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_document: dict[str, dict[str, Any]] = {}
    for record in records:
        source = record.get("source_file")
        stats = by_document.setdefault(
            source,
            {
                "source_file": source,
                "domain": record.get("domain"),
                "document_type": record.get("document_type"),
                "total_chunks": 0,
                "structure_aware_chunks": 0,
                "fallback_chunks": 0,
                "counts_by_structure_type": Counter(),
            },
        )
        stats["total_chunks"] += 1
        stats["counts_by_structure_type"][record.get("structure_type")] += 1
        if record.get("structure_type") == "fallback":
            stats["fallback_chunks"] += 1
        else:
            stats["structure_aware_chunks"] += 1
    output = []
    for stats in by_document.values():
        total = stats["total_chunks"] or 1
        output.append(
            {
                **{key: value for key, value in stats.items() if key != "counts_by_structure_type"},
                "structure_aware_percentage": round(stats["structure_aware_chunks"] / total * 100, 2),
                "counts_by_structure_type": dict(stats["counts_by_structure_type"]),
            }
        )
    return sorted(output, key=lambda item: item["source_file"])


def manifest_consistency(records: list[dict[str, Any]], manifest: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    for record in records:
        source = record.get("source_file")
        manifest_entry = manifest.get(source)
        if not manifest_entry:
            add_issue(issues, "HIGH", "missing_manifest_entry", "No manifest entry for source_file", record)
            continue
        for field in MANIFEST_FIELDS:
            if record.get(field) != manifest_entry.get(field):
                add_issue(
                    issues,
                    "HIGH",
                    "manifest_metadata_mismatch",
                    f"Chunk metadata for {field} does not match manifest",
                    record,
                    field=field,
                    chunk_value=record.get(field),
                    manifest_value=manifest_entry.get(field),
                )
    return issues


def archive_manual_safety(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    for record in records:
        source = str(record.get("source_file") or "")
        if source.startswith("archive/"):
            add_issue(issues, "HIGH", "archive_document_included", "Archived document appears in chunks", record)
        if record.get("status") == "manual_verification_required":
            add_issue(
                issues,
                "HIGH",
                "manual_verification_document_included",
                "Manual-verification document appears in chunks",
                record,
            )
    return issues


def severity_counts(*issue_groups: Any) -> dict[str, int]:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            severity = value.get("severity")
            if severity in counts:
                counts[severity] += 1

    for group in issue_groups:
        visit(group)
    return counts


def build_audit(records: list[dict[str, Any]], manifest: dict[str, dict[str, Any]]) -> dict[str, Any]:
    basic = validate_basic_records(records)
    provision = validate_provision_metadata(records)
    short = short_chunk_findings(records)
    large = large_chunk_findings(records)
    duplicates = duplicate_findings(records)
    noise = header_footer_noise_findings(records)
    sequence = sequence_anomalies(records)
    child = child_chunk_issues(records)
    pages = page_range_issues(records)
    fallback = fallback_statistics(records)
    coverage = structure_coverage(records)
    manifest_issues = manifest_consistency(records, manifest)
    safety = archive_manual_safety(records)

    low_info = []
    if short["very_suspicious_under_40_count"]:
        low_info.append({"severity": "LOW", "type": "very_short_chunks", "count": short["very_suspicious_under_40_count"]})
    if short["review_40_to_100_count"]:
        low_info.append({"severity": "LOW", "type": "short_review_chunks", "count": short["review_40_to_100_count"]})
    if noise["suspicious_pattern_count"]:
        low_info.append({"severity": "LOW", "type": "header_footer_noise_patterns", "count": noise["suspicious_pattern_count"]})
    medium_info = []
    if large["review_over_8000_count"]:
        medium_info.append({"severity": "MEDIUM", "type": "large_chunks_over_8000", "count": large["review_over_8000_count"]})
    if duplicates["exact_duplicate_group_count"]:
        medium_info.append({"severity": "MEDIUM", "type": "exact_duplicate_text_groups", "count": duplicates["exact_duplicate_group_count"]})
    if duplicates["near_duplicate_group_count"]:
        medium_info.append({"severity": "MEDIUM", "type": "near_duplicate_text_groups", "count": duplicates["near_duplicate_group_count"]})
    high_info = []
    if large["high_priority_over_15000_count"]:
        high_info.append({"severity": "HIGH", "type": "huge_chunks_over_15000", "count": large["high_priority_over_15000_count"]})

    counts = severity_counts(
        basic,
        provision,
        sequence,
        child,
        pages,
        manifest_issues,
        safety,
        low_info,
        medium_info,
        high_info,
    )
    status = "PASS"
    if counts["HIGH"]:
        status = "NEEDS FIXES"
    elif counts["MEDIUM"] or counts["LOW"]:
        status = "PASS WITH WARNINGS"

    return {
        "audit_summary": {
            "status": status,
            "total_chunks_checked": len(records),
            "unique_chunk_ids": len({record.get("chunk_id") for record in records if record.get("chunk_id")}),
            "severity_counts": counts,
        },
        "validation_failures": basic,
        "provision_metadata_inconsistencies": provision,
        "suspicious_short_chunks": short,
        "suspicious_large_chunks": large,
        "duplicate_findings": duplicates,
        "header_footer_noise": noise,
        "sequence_anomalies": sequence,
        "child_chunk_issues": child,
        "page_range_issues": pages,
        "fallback_statistics": fallback,
        "per_document_quality_metrics": coverage,
        "manifest_inconsistencies": manifest_issues,
        "archive_manual_review_safety": safety,
    }


def markdown_report(audit: dict[str, Any]) -> str:
    summary = audit["audit_summary"]
    fallback = audit["fallback_statistics"]
    top_fallback = fallback["by_document_ranked"][:8]
    largest = audit["suspicious_large_chunks"]["top_20_largest"][:10]
    duplicate = audit["duplicate_findings"]
    noise = audit["header_footer_noise"]["patterns"][:8]
    counts = summary["severity_counts"]
    problematic = [
        doc for doc in fallback["by_document_ranked"]
        if doc["fallback_percentage"] >= 20 or doc["fallback_chunks"] >= 10
    ][:10]

    lines = [
        "# Ingestion Audit Summary",
        "",
        "## Overall Results",
        f"- Status: {summary['status']}",
        f"- Total chunks checked: {summary['total_chunks_checked']}",
        f"- Unique chunk IDs: {summary['unique_chunk_ids']}",
        f"- HIGH findings: {counts['HIGH']}",
        f"- MEDIUM findings: {counts['MEDIUM']}",
        f"- LOW findings: {counts['LOW']}",
        "",
        "## High-Priority Issues",
    ]
    high_issue_count = counts["HIGH"]
    lines.append("- None found." if high_issue_count == 0 else f"- {high_issue_count} high-priority finding(s). See JSON report for exact records.")
    lines.extend(["", "## Medium-Priority Issues"])
    if counts["MEDIUM"] == 0:
        lines.append("- None found.")
    else:
        lines.append(f"- {counts['MEDIUM']} medium-priority finding(s), mainly review-scale quality signals.")
        lines.append(f"- Large chunks over 8,000 characters: {audit['suspicious_large_chunks']['review_over_8000_count']}")
        lines.append(f"- Exact duplicate text groups: {duplicate['exact_duplicate_group_count']}")
        lines.append(f"- Near-duplicate text groups: {duplicate['near_duplicate_group_count']}")
    lines.extend(["", "## Low-Priority / Informational Findings"])
    lines.append(f"- Very short chunks under 40 characters: {audit['suspicious_short_chunks']['very_suspicious_under_40_count']}")
    lines.append(f"- Review-candidate chunks from 40 to 100 characters: {audit['suspicious_short_chunks']['review_40_to_100_count']}")
    lines.append(f"- Suspicious recurring header/footer patterns: {audit['header_footer_noise']['suspicious_pattern_count']}")
    lines.extend(["", "## Documents Requiring Attention"])
    if not problematic:
        lines.append("- No document crossed the high fallback attention threshold.")
    else:
        for doc in problematic:
            lines.append(
                f"- `{doc['source_file']}`: {doc['fallback_chunks']} fallback chunks "
                f"({doc['fallback_percentage']}%)"
            )
    lines.extend(["", "## Fallback Analysis"])
    lines.append(f"- Total fallback chunks: {fallback['total_fallback_chunks']}")
    for doc in top_fallback:
        lines.append(
            f"- `{doc['source_file']}`: {doc['fallback_chunks']}/{doc['total_chunks']} "
            f"fallback ({doc['fallback_percentage']}%)"
        )
    lines.extend(["", "## Largest Chunks"])
    for item in largest:
        lines.append(
            f"- `{item['chunk_id']}` in `{item['source_file']}`: "
            f"{item['char_count']} chars, {item['structure_type']} {item.get('provision_number') or ''}"
        )
    lines.extend(["", "## Duplicate / Noise Findings"])
    lines.append(f"- Exact duplicate groups: {duplicate['exact_duplicate_group_count']}")
    lines.append(f"- Near-duplicate groups: {duplicate['near_duplicate_group_count']}")
    if noise:
        lines.append("- Recurring noise examples:")
        for item in noise:
            lines.append(f"  - `{item['text'][:120]}` ({item['count']} occurrences)")
    lines.extend(["", "## Recommended Next Actions"])
    if summary["status"] == "NEEDS FIXES":
        lines.append("- Proceed to Part 5B parser fixes before rebuilding the index.")
    elif counts["MEDIUM"] or counts["LOW"]:
        lines.append("- Review the warnings in `ingestion_audit.json`; proceed to Part 5B only for findings worth fixing.")
    else:
        lines.append("- No parser fixes are required by this audit; proceed toward index rebuild when ready.")
    lines.append("")
    return "\n".join(lines)


def write_audit_reports(
    audit: dict[str, Any],
    json_path: Path = AUDIT_JSON_PATH,
    md_path: Path = AUDIT_MD_PATH,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(audit), encoding="utf-8")


def run_audit(
    chunks_path: Path = LEGAL_CHUNKS_PATH,
    manifest_path: Path = CORPUS_MANIFEST_PATH,
    json_path: Path = AUDIT_JSON_PATH,
    md_path: Path = AUDIT_MD_PATH,
) -> dict[str, Any]:
    records = load_jsonl(chunks_path)
    manifest = load_manifest(manifest_path)
    audit = build_audit(records, manifest)
    write_audit_reports(audit, json_path=json_path, md_path=md_path)
    return audit


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Audit saved legal chunk JSONL output.")
    parser.add_argument("--chunks", type=Path, default=LEGAL_CHUNKS_PATH)
    parser.add_argument("--manifest", type=Path, default=CORPUS_MANIFEST_PATH)
    parser.add_argument("--json-output", type=Path, default=AUDIT_JSON_PATH)
    parser.add_argument("--md-output", type=Path, default=AUDIT_MD_PATH)
    args = parser.parse_args(argv)
    audit = run_audit(args.chunks, args.manifest, args.json_output, args.md_output)
    summary = audit["audit_summary"]
    print(
        f"Audit {summary['status']}: {summary['total_chunks_checked']} chunks checked; "
        f"HIGH={summary['severity_counts']['HIGH']}, "
        f"MEDIUM={summary['severity_counts']['MEDIUM']}, "
        f"LOW={summary['severity_counts']['LOW']}"
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.md_output}")
    return audit


if __name__ == "__main__":
    main()
