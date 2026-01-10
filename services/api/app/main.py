from fastapi import FastAPI
from app.core.config import settings
from app.routers import health

def create_app() -> FastAPI:
    api = FastAPI(title=settings.app_name)

    api.include_router(health.router)
    return api

app = create_app()
