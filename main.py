import asyncio
import uvicorn
from services import logic
from database import init_db
from contextlib import asynccontextmanager
from fastapi import FastAPI

#folders
from core.config import settings
from api import router as api_router

@asynccontextmanager
async def lifespan():
    print("Работаем, братья!")
    print("Starting bot...")

    print("Сервису жёпа!!!")
    yield

app = FastAPI()
app.include_router(api_router, prefix=settings.api.prefix)

@app.get("/setting")
async def setting_chack():
    return {"status": "Bot is running"}

if __name__ == '__main__':
    uvicorn.run("main.py", host = settings.run.host, port = settings.run.port, reload=True)
    asyncio.run(init_db())
    pay = logic.Payments()

