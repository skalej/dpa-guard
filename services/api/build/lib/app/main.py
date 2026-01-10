from fastapi import FastAPI
from app.core.config import settings
from app.routers import health

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.include_router(health.router)
    return app