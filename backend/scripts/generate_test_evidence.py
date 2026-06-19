from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESULTS_ROOT = Path("/app/results")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


def parse_pytest(text: str) -> dict[str, Any]:
    result = {
        "status": "not_available",
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "warnings": 0,
        "summary": "",
    }
    matches = re.findall(r"=+\s*([^=\n]*(?:passed|failed|error|errors|warning|warnings)[^=\n]*)\s*=+", text, re.I)
    if matches:
        result["summary"] = matches[-1].strip()
    else:
        lines = [line.strip() for line in text.splitlines() if "passed" in line or "failed" in line or "error" in line]
        result["summary"] = lines[-1] if lines else ""

    summary = result["summary"]
    for key, pattern in {
        "passed": r"(\d+)\s+passed",
        "failed": r"(\d+)\s+failed",
        "errors": r"(\d+)\s+errors?",
        "warnings": r"(\d+)\s+warnings?",
    }.items():
        match = re.search(pattern, summary, re.I)
        if match:
            result[key] = int(match.group(1))

    if result["failed"] or result["errors"]:
        result["status"] = "failed"
    elif result["passed"]:
        result["status"] = "passed"
    return result


def parse_rasa_e2e(text: str) -> dict[str, Any]:
    result = {
        "status": "not_available",
        "passed": 0,
        "failed": 0,
        "cases": 0,
        "summary": "",
        "failed_cases": [],
    }
    match = re.search(r"=+\s*(\d+)\s+failed,\s*(\d+)\s+passed\s*=+", text, re.I)
    if match:
        result["failed"] = int(match.group(1))
        result["passed"] = int(match.group(2))
    else:
        match = re.search(r"=+\s*(\d+)\s+passed\s*=+", text, re.I)
        if match:
            result["passed"] = int(match.group(1))

    result["cases"] = result["passed"] + result["failed"]
    result["summary"] = f"{result['passed']} passed, {result['failed']} failed"
    result["failed_cases"] = re.findall(r"FAILED\s+[^:]+::([^\n]+)", text)

    if result["cases"] == 0 or "no test cases found" in text.lower():
        result["status"] = "invalid_zero_tests"
    elif result["failed"]:
        result["status"] = "failed"
    elif result["passed"]:
        result["status"] = "passed"
    return result


def parse_rasa_nlu(report: Any, errors: Any) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {"status": "not_available", "accuracy": None, "macro_f1": None, "weighted_f1": None, "errors": None}
    accuracy = report.get("accuracy")
    macro = report.get("macro avg") if isinstance(report.get("macro avg"), dict) else {}
    weighted = report.get("weighted avg") if isinstance(report.get("weighted avg"), dict) else {}
    return {
        "status": "diagnostic",
        "accuracy": accuracy,
        "macro_f1": macro.get("f1-score"),
        "weighted_f1": weighted.get("f1-score"),
        "errors": len(errors) if isinstance(errors, list) else None,
    }


def parse_rasa_core(report: Any, failed_text: str) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {"status": "not_available", "accuracy": None, "f1": None, "failed_stories": None}
    accuracy = report.get("accuracy")
    f1 = report.get("f1-score") or report.get("f1")
    failed_stories = failed_text.count("- story:") if failed_text else 0
    return {
        "status": "diagnostic",
        "accuracy": accuracy,
        "f1": f1,
        "failed_stories": failed_stories,
    }


def status_class(status: str) -> str:
    if status in {"passed", "completed"}:
        return "pass"
    if status.startswith("failed") or status == "invalid_zero_tests":
        return "fail"
    if status in {"warning", "diagnostic"}:
        return "warn"
    return "neutral"


def build_evidence() -> dict[str, Any]:
    pytest_text = read_text(RESULTS_ROOT / "pytest_results.txt")
    e2e_text = read_text(RESULTS_ROOT / "rasa" / "e2e" / "rasa_e2e_results.txt")
    nlu_report = read_json(RESULTS_ROOT / "rasa" / "nlu" / "intent_report.json")
    nlu_errors = read_json(RESULTS_ROOT / "rasa" / "nlu" / "intent_errors.json")
    core_report = read_json(RESULTS_ROOT / "rasa" / "core" / "story_report.json")
    core_failed = read_text(RESULTS_ROOT / "rasa" / "core" / "failed_test_stories.yml")

    pytest = parse_pytest(pytest_text)
    rasa_e2e = parse_rasa_e2e(e2e_text)
    rasa_nlu = parse_rasa_nlu(nlu_report, nlu_errors)
    rasa_core = parse_rasa_core(core_report, core_failed)

    areas = [
        {
            "area": "Pytest Unit Tests",
            "status": pytest["status"],
            "metric": pytest["summary"],
            "evidence_type": "Primary deterministic unit evidence",
            "artifact": "/api/test-results/pytest",
        },
        {
            "area": "Rasa E2E",
            "status": rasa_e2e["status"],
            "metric": rasa_e2e["summary"],
            "evidence_type": "Primary CALM dialogue evidence",
            "artifact": "/api/test-results/rasa-e2e",
        },
        {
            "area": "Rasa NLU",
            "status": rasa_nlu["status"],
            "metric": f"accuracy={rasa_nlu.get('accuracy')}, macro_f1={rasa_nlu.get('macro_f1')}",
            "evidence_type": "Classic compatibility diagnostic",
            "artifact": "/api/test-results/rasa/nlu/intent-report",
        },
        {
            "area": "Rasa Core",
            "status": rasa_core["status"],
            "metric": f"accuracy={rasa_core.get('accuracy')}, f1={rasa_core.get('f1')}, failed_stories={rasa_core.get('failed_stories')}",
            "evidence_type": "Classic compatibility diagnostic",
            "artifact": "/api/test-results/rasa/core/story-report",
        },
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app_env": "TEST",
        "overall_status": "failed" if any(item["status"].startswith("failed") for item in areas) else "passed_with_diagnostics",
        "areas": areas,
        "pytest": pytest,
        "rasa_e2e": rasa_e2e,
        "rasa_nlu": rasa_nlu,
        "rasa_core": rasa_core,
        "limitations": [
            "Rasa NLU/Core are compatibility diagnostics for a CALM assistant.",
            "Raw logs remain available as supporting artifacts, not primary evidence.",
        ],
    }


def write_csv(evidence: dict[str, Any]) -> None:
    path = RESULTS_ROOT / "test_evidence_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["area", "status", "metric", "evidence_type", "artifact"])
        writer.writeheader()
        writer.writerows(evidence["areas"])


def write_markdown(evidence: dict[str, Any]) -> None:
    rows = "\n".join(
        f"| {item['area']} | {item['status']} | {item['metric']} | {item['evidence_type']} | `{item['artifact']}` |"
        for item in evidence["areas"]
    )
    content = f"""# NovaPlan Backend Runtime Validation Report

Generated inside the Hugging Face Docker container by `APP_ENV=TEST`.

## Evidence Summary

| Area | Status | Metric | Evidence Type | Artifact |
|---|---|---|---|---|
{rows}

## Interpretation

- Pytest and Rasa E2E are primary evidence.
- Rasa NLU/Core are compatibility diagnostics because NovaPlan uses Rasa Pro CALM.
- Raw logs are supporting artifacts only.
"""
    (RESULTS_ROOT / "backend_validation_report.md").write_text(content, encoding="utf-8")


def write_html(evidence: dict[str, Any]) -> None:
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(item['area'])}</td>"
        f"<td><span class='{status_class(item['status'])}'>{html.escape(item['status'])}</span></td>"
        f"<td>{html.escape(str(item['metric']))}</td>"
        f"<td>{html.escape(item['evidence_type'])}</td>"
        f"<td><a href='{html.escape(item['artifact'])}'>{html.escape(item['artifact'])}</a></td>"
        "</tr>"
        for item in evidence["areas"]
    )
    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>NovaPlan Backend Validation Evidence</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #0f172a; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; }}
    .pass {{ color: #047857; font-weight: 700; }}
    .fail {{ color: #b91c1c; font-weight: 700; }}
    .warn {{ color: #a16207; font-weight: 700; }}
    .neutral {{ color: #475569; font-weight: 700; }}
    .note {{ background: #f8fafc; border: 1px solid #cbd5e1; padding: 12px; margin-top: 20px; }}
  </style>
</head>
<body>
  <h1>NovaPlan Backend Validation Evidence</h1>
  <p><strong>Generated:</strong> {html.escape(evidence['generated_at'])}</p>
  <p><strong>Overall status:</strong> {html.escape(evidence['overall_status'])}</p>
  <table>
    <thead>
      <tr><th>Area</th><th>Status</th><th>Metric</th><th>Evidence Type</th><th>Artifact</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="note">
    <p>Pytest and Rasa E2E are primary evidence. Rasa NLU/Core are compatibility diagnostics for this CALM assistant.</p>
    <p>Raw logs remain available as supporting artifacts.</p>
  </div>
</body>
</html>
"""
    (RESULTS_ROOT / "evidence_report.html").write_text(content, encoding="utf-8")


def main() -> None:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence()
    (RESULTS_ROOT / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    (RESULTS_ROOT / "evidence_tables.json").write_text(json.dumps(evidence["areas"], indent=2), encoding="utf-8")
    write_csv(evidence)
    write_markdown(evidence)
    write_html(evidence)
    (RESULTS_ROOT / "test_summary.txt").write_text(
        "\n".join(
            [
                f"Generated: {evidence['generated_at']}",
                f"Overall status: {evidence['overall_status']}",
                *[f"{item['area']}: {item['status']} ({item['metric']})" for item in evidence["areas"]],
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
