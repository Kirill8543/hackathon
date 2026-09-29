import asyncio
import uvicorn
import httpx
from services import logic
from database import init_db
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends

#folders
from core.config import settings
from api import router as api_router
from services.logic import Payments
from core.config import CostRequest

@asynccontextmanager
async def lifespan():
    print("Работаем, братья!")
    print("Starting bot...")

    print("Не готов!!!")
    yield

app = FastAPI(
    title="VK_MAX Tax Bot",
    description="Бот для автоматизации налоговых расчетов",
    version="1.0.0"
)
app.include_router(api_router, prefix=settings.api.prefix)


def get_logic() -> Payments:
    return Payments()




async def send_notification_to_vk_max(message: str):
    headers = {
        "Authorization": f"Bearer {settings.VK_MAX_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"text": message, "source": "tax_bot"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.Vk_MAX_API_URL}/webhook/bot",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"[ERROR] Не удалось отправить уведомление: {e}")
            return None


@app.get(f"{settings.api.prefix}/health")
async def health_check():
    return {"status": "ok"}


@app.get(f"{settings.api.prefix}/dates/prepayment_usn")
async def get_prepayment_usn(logic: Payments = Depends(get_logic)):
    return {"date": logic.date_prepayment_usn().isoformat()}


@app.get(f"{settings.api.prefix}/dates/fix_payment")
async def get_fix_payment(logic: Payments = Depends(get_logic)):
    return {"date": logic.date_fix_payment().isoformat()}


@app.get(f"{settings.api.prefix}/dates/add_fix_payment")
async def get_add_fix_payment(logic: Payments = Depends(get_logic)):
    return {"date": logic.date_add_fix_payment().isoformat()}


@app.get(f"{settings.api.prefix}/dates/declaration_nds")
async def get_declaration_nds(logic: Payments = Depends(get_logic)):
    return {"date": logic.date_declaration_nds().isoformat()}


@app.get(f"{settings.api.prefix}/dates/payment_nds")
async def get_payment_nds(logic: Payments = Depends(get_logic)):
    dates = logic.date_payment_nds()
    return {"dates": [d.isoformat() for d in dates]}


@app.post(f"{settings.api.prefix}/calc/cost_with_nds")
async def calc_cost_with_nds(request: CostRequest, logic: Payments = Depends(get_logic)):
    result = logic.cost_with_nds(request.cost)
    return {"original_cost": request.cost, "cost_with_nds": result}


@app.get(f"{settings.api.prefix}/fix_payment_amount")
async def get_fix_payment_amount(logic: Payments = Depends(get_logic)):
    return {"amount": logic.fix_payment()}

if __name__ == '__main__':
    uvicorn.run("main.py", host = settings.run.host, port = settings.run.port, reload=True)
    asyncio.run(init_db())
    pay = logic.Payments()

