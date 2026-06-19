from fastapi import APIRouter, HTTPException

from ..health_service import HealthService

router = APIRouter(tags=["health"])
_health = HealthService()


@router.get("/health/database")
async def health_database():
    try:
        return _health.database()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/health/db")
async def health_database_legacy():
    return await health_database()


@router.get("/health/rasa")
async def health_rasa():
    result = await _health.rasa()
    if result.get("status") == "error":
        raise HTTPException(status_code=503, detail=result)
    return result


@router.get("/health/actions")
async def health_actions():
    return await _health.actions()


@router.get("/health/integrations")
async def health_integrations():
    return await _health.integrations()


@router.get("/health")
async def health_aggregate():
    return await _health.aggregate()
