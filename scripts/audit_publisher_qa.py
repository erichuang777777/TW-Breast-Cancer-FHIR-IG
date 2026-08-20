#!/usr/bin/env python3
"""Fail when IG Publisher QA contains unclassified or increased warnings."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path


TEXT_SUMMARY = re.compile(r"^err = (\d+), warn = (\d+), info = (\d+)$", re.MULTILINE)
HTML_SUMMARY = re.compile(
    r"broken links = (\d+), errors = (\d+), warn = (\d+), info = (\d+)"
)


def load_policy(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "warning_id", "pattern", "max_count", "preview_disposition",
        "formal_disposition", "reason", "owner", "required_evidence",
        "preview_approval_status", "approved_by", "approval_date",
        "approval_expiry",
    }
    if not rows or set(rows[0]) != required:
        raise ValueError(f"{path}: expected columns {sorted(required)}")
    if len({row["warning_id"] for row in rows}) != len(rows):
        raise ValueError(f"{path}: warning_id values must be unique")
    for row in rows:
        row["max_count"] = int(row["max_count"])
        row["compiled_pattern"] = re.compile(str(row["pattern"]))
        if row["formal_disposition"] != "block":
            raise ValueError(
                f"{path}: {row['warning_id']} must block formal release while present"
            )
        if row["preview_approval_status"] not in {"pending", "approved"}:
            raise ValueError(
                f"{path}: {row['warning_id']} has invalid preview_approval_status"
            )
        if row["preview_approval_status"] == "approved" and not all(
            str(row[field]).strip()
            for field in ("approved_by", "approval_date", "approval_expiry")
        ):
            raise ValueError(
                f"{path}: approved warning {row['warning_id']} needs approver, date, and expiry"
            )
        row["approval_valid"] = False
        if row["preview_approval_status"] == "approved":
            try:
                approved = date.fromisoformat(str(row["approval_date"]))
                expiry = date.fromisoformat(str(row["approval_expiry"]))
            except ValueError as exc:
                raise ValueError(
                    f"{path}: {row['warning_id']} approval dates must be YYYY-MM-DD"
                ) from exc
            if expiry < approved:
                raise ValueError(
                    f"{path}: {row['warning_id']} approval expires before approval date"
                )
            row["approval_valid"] = expiry >= date.today()
        for field in ("reason", "owner", "required_evidence"):
            if not str(row[field]).strip():
                raise ValueError(f"{path}: {row['warning_id']} has empty {field}")
    return rows


def audit(qa_text: Path, qa_html: Path, policy_path: Path) -> dict[str, object]:
    text = qa_text.read_text(encoding="utf-8")
    html = qa_html.read_text(encoding="utf-8")
    text_match = TEXT_SUMMARY.search(text)
    html_match = HTML_SUMMARY.search(html)
    if text_match is None or html_match is None:
        raise ValueError("Publisher QA summary is missing or has an unexpected format")

    errors, warning_total, information = map(int, text_match.groups())
    broken_links, html_errors, html_warnings, html_information = map(
        int, html_match.groups()
    )
    if (errors, warning_total, information) != (
        html_errors, html_warnings, html_information
    ):
        raise ValueError("qa.txt and qa.html summary counts disagree")

    warning_lines = [line for line in text.splitlines() if line.startswith("WARNING:")]
    if len(warning_lines) != warning_total:
        raise ValueError(
            f"QA says {warning_total} warnings but qa.txt contains "
            f"{len(warning_lines)} WARNING lines"
        )

    policy = load_policy(policy_path)
    counts: Counter[str] = Counter()
    unknown: list[str] = []
    ambiguous: list[dict[str, object]] = []
    for warning in warning_lines:
        matches = [
            str(row["warning_id"])
            for row in policy
            if row["compiled_pattern"].search(warning)  # type: ignore[union-attr]
        ]
        if not matches:
            unknown.append(warning)
        elif len(matches) > 1:
            ambiguous.append({"warning": warning, "matches": matches})
        else:
            counts[matches[0]] += 1

    categories = []
    over_limit = []
    for row in policy:
        warning_id = str(row["warning_id"])
        count = counts[warning_id]
        maximum = int(row["max_count"])
        category = {
            key: value
            for key, value in row.items()
            if key not in {"compiled_pattern", "pattern"}
        }
        category.update({"observed_count": count, "within_limit": count <= maximum})
        categories.append(category)
        if count > maximum:
            over_limit.append(
                {"warning_id": warning_id, "observed_count": count, "max_count": maximum}
            )

    failures = []
    if errors:
        failures.append(f"{errors} Publisher errors")
    if broken_links:
        failures.append(f"{broken_links} broken links")
    if unknown:
        failures.append(f"{len(unknown)} unclassified warnings")
    if ambiguous:
        failures.append(f"{len(ambiguous)} ambiguously classified warnings")
    if over_limit:
        failures.append(f"{len(over_limit)} warning categories exceed their limit")

    preview_blocking = [
        category["warning_id"]
        for category in categories
        if category["observed_count"]
        and (
            str(category["preview_disposition"]).startswith("must-")
            or category["preview_approval_status"] != "approved"
            or not category["approval_valid"]
        )
    ]
    return {
        "qa": {
            "errors": errors,
            "warnings": warning_total,
            "information": information,
            "broken_links": broken_links,
        },
        "policy": str(policy_path),
        "categories": categories,
        "unknown_warnings": unknown,
        "ambiguous_warnings": ambiguous,
        "over_limit": over_limit,
        "qa_integrity_gate": "pass" if not failures else "fail",
        "community_preview_gate": (
            "pass" if not failures and not preview_blocking else "block"
        ),
        "formal_release_gate": "pass" if not failures and warning_total == 0 else "block",
        "preview_blocking_categories": preview_blocking,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa-text", type=Path, required=True)
    parser.add_argument("--qa-html", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--target", choices=("integrity", "preview", "formal"), default="integrity"
    )
    args = parser.parse_args()

    try:
        report = audit(args.qa_text, args.qa_html, args.policy)
    except (OSError, ValueError, csv.Error, re.error) as exc:
        print(f"Publisher QA audit failed: {exc}", file=sys.stderr)
        return 2

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    qa = report["qa"]
    print(
        "Publisher QA: "
        f"{qa['errors']} errors, {qa['warnings']} warnings, "
        f"{qa['broken_links']} broken links"
    )
    for category in report["categories"]:
        print(
            f"- {category['warning_id']}: {category['observed_count']} / "
            f"max {category['max_count']} ({category['preview_disposition']})"
        )
    print(f"QA integrity gate: {report['qa_integrity_gate']}")
    print(f"Community Preview gate: {report['community_preview_gate']}")
    print(f"Formal release gate: {report['formal_release_gate']}")
    for failure in report["failures"]:
        print(f"FAIL: {failure}", file=sys.stderr)
    selected = {
        "integrity": "qa_integrity_gate",
        "preview": "community_preview_gate",
        "formal": "formal_release_gate",
    }[args.target]
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
