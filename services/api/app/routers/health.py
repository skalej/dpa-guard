from fastapi import APIRouter
from sqlalchemy import text

from services.api.app.db.session import SessionLocal

router = APIRouter(tags=["Health"])

@router.get("/health/live", summary="Liveness Probe")
def live():
    return {"status": "ok"}

@router.get("/health/ready")
def ready():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}