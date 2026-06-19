from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from config.settings import APP_ENV

router = APIRouter(tags=["test-results"])

RESULTS_ROOT = Path("/app/results")
FILES = {
    "summary": RESULTS_ROOT / "test_summary.txt",
    "report": RESULTS_ROOT / "backend_validation_report.md",
    "report-html": RESULTS_ROOT / "evidence_report.html",
    "evidence": RESULTS_ROOT / "test_evidence_summary.csv",
    "evidence-json": RESULTS_ROOT / "evidence.json",
    "evidence-tables": RESULTS_ROOT / "evidence_tables.json",
    "pytest": RESULTS_ROOT / "pytest_results.txt",
    "rasa-e2e": RESULTS_ROOT / "rasa" / "e2e" / "rasa_e2e_results.txt",
    "rasa-action-server": RESULTS_ROOT / "rasa_action_server_test.log",
    "rasa-nlu-intents": RESULTS_ROOT / "rasa" / "nlu" / "intent_report.json",
    "rasa-nlu-errors": RESULTS_ROOT / "rasa" / "nlu" / "intent_errors.json",
    "rasa-core-stories": RESULTS_ROOT / "rasa" / "core" / "story_report.json",
    "rasa-core-failed-stories": RESULTS_ROOT / "rasa" / "core" / "failed_test_stories.yml",
}


def _require_test_mode() -> None:
    if APP_ENV != "TEST":
        raise HTTPException(status_code=404, detail="Not found")


def _file_response(key: str, media_type: str) -> FileResponse:
    _require_test_mode()
    path = FILES[key]
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Test result not found: {key}")
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/test-results")
def list_test_results():
    _require_test_mode()
    return {
        "appEnv": APP_ENV,
        "available": {key: path.exists() for key, path in FILES.items()},
        "endpoints": {
            "summary": "/api/test-results/summary",
            "report": "/api/test-results/report",
            "reportHtml": "/api/test-results/report.html",
            "evidence": "/api/test-results/evidence.csv",
            "evidenceJson": "/api/test-results/evidence.json",
            "evidenceTables": "/api/test-results/evidence/tables",
            "pytest": "/api/test-results/pytest",
            "rasaE2e": "/api/test-results/rasa-e2e",
            "rasaActionServer": "/api/test-results/rasa-action-server",
            "rasaNluIntents": "/api/test-results/rasa/nlu/intent-report",
            "rasaNluErrors": "/api/test-results/rasa/nlu/intent-errors",
            "rasaCoreStories": "/api/test-results/rasa/core/story-report",
            "rasaCoreFailedStories": "/api/test-results/rasa/core/failed-stories",
        },
    }


@router.get("/test-results/summary", response_class=PlainTextResponse)
def get_summary():
    return _file_response("summary", "text/plain")


@router.get("/test-results/report")
def get_report():
    return _file_response("report", "text/markdown")


@router.get("/test-results/report.html")
def get_report_html():
    return _file_response("report-html", "text/html")


@router.get("/test-results/evidence.csv")
def get_evidence():
    return _file_response("evidence", "text/csv")


@router.get("/test-results/evidence.json")
def get_evidence_json():
    return _file_response("evidence-json", "application/json")


@router.get("/test-results/evidence/tables")
def get_evidence_tables():
    return _file_response("evidence-tables", "application/json")


@router.get("/test-results/pytest", response_class=PlainTextResponse)
def get_pytest_results():
    return _file_response("pytest", "text/plain")


@router.get("/test-results/rasa-e2e", response_class=PlainTextResponse)
def get_rasa_e2e_results():
    return _file_response("rasa-e2e", "text/plain")


@router.get("/test-results/rasa-action-server", response_class=PlainTextResponse)
def get_rasa_action_server_log():
    return _file_response("rasa-action-server", "text/plain")


@router.get("/test-results/rasa/nlu/intent-report")
def get_rasa_nlu_intent_report():
    return _file_response("rasa-nlu-intents", "application/json")


@router.get("/test-results/rasa/nlu/intent-errors")
def get_rasa_nlu_intent_errors():
    return _file_response("rasa-nlu-errors", "application/json")


@router.get("/test-results/rasa/core/story-report")
def get_rasa_core_story_report():
    return _file_response("rasa-core-stories", "application/json")


@router.get("/test-results/rasa/core/failed-stories", response_class=PlainTextResponse)
def get_rasa_core_failed_stories():
    return _file_response("rasa-core-failed-stories", "text/yaml")
