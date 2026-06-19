from pathlib import Path
import importlib.util

import pytest
from fastapi import HTTPException

MODULE_PATH = Path(__file__).resolve().parents[1] / "api" / "services" / "routes" / "test_results.py"
SPEC = importlib.util.spec_from_file_location("test_results_route", MODULE_PATH)
test_results = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(test_results)


def test_test_results_blocked_outside_test(monkeypatch):
    monkeypatch.setattr(test_results, "APP_ENV", "PROD")

    with pytest.raises(HTTPException) as exc:
        test_results.list_test_results()

    assert exc.value.status_code == 404


def test_test_results_index_in_test_mode(tmp_path, monkeypatch):
    report = tmp_path / "backend_validation_report.md"
    report.write_text("# report", encoding="utf-8")
    monkeypatch.setattr(test_results, "APP_ENV", "TEST")
    monkeypatch.setattr(test_results, "RESULTS_ROOT", tmp_path)
    monkeypatch.setattr(
        test_results,
        "FILES",
        {
            "report": report,
            "summary": tmp_path / "missing.txt",
        },
    )

    result = test_results.list_test_results()

    assert result["appEnv"] == "TEST"
    assert result["available"]["report"] is True
    assert result["available"]["summary"] is False


def test_test_results_file_response_uses_fixed_file(tmp_path, monkeypatch):
    summary = tmp_path / "test_summary.txt"
    summary.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(test_results, "APP_ENV", "TEST")
    monkeypatch.setattr(test_results, "FILES", {"summary": summary})

    response = test_results.get_summary()

    assert Path(response.path) == summary


def test_structured_evidence_endpoints(tmp_path, monkeypatch):
    files = {
        "report-html": tmp_path / "evidence_report.html",
        "evidence-json": tmp_path / "evidence.json",
        "evidence-tables": tmp_path / "evidence_tables.json",
    }
    files["report-html"].write_text("<html></html>", encoding="utf-8")
    files["evidence-json"].write_text("{}", encoding="utf-8")
    files["evidence-tables"].write_text("[]", encoding="utf-8")

    monkeypatch.setattr(test_results, "APP_ENV", "TEST")
    monkeypatch.setattr(test_results, "FILES", files)

    assert Path(test_results.get_report_html().path) == files["report-html"]
    assert Path(test_results.get_evidence_json().path) == files["evidence-json"]
    assert Path(test_results.get_evidence_tables().path) == files["evidence-tables"]
