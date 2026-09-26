import asyncio
from services import logic
from database import init_db



if __name__ == '__main__':
    asyncio.run(init_db())
    pay = logic.Payments()

