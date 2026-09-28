import asyncio
from services import logic
from database import init_db

#
#
# if __name__ == '__main__':
#     asyncio.run(init_db())
#     pay = logic.Payments()


async def main():
    pay = logic.Payments()
    pay.user_id = "123"
    print(await pay.NDS.cost_with_nds("123", 1000102))
    print(await pay.NDS.check_nds("123"))

asyncio.run(main())