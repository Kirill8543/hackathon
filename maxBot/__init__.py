from fastapi import FastAPI
from core.config import settings
from api import router as api_router




app = FastAPI(
        title="VK_MAX Tax Bot",
        description="Бот для автоматизации налоговых расчетов",
        version="1.0.0"
    )
app.include_router(api_router, prefix=settings.api.prefix)