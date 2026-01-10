from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health/live", summary="Liveness Probe")
def live():
    return {"status": "ok"}

@router.get("/health/ready", summary="Readiness Probe")
def ready():
    # Step 1: always ready. In Step 2 we'll check DB/Redis/MinIO here.
    return {"status": "ok"}