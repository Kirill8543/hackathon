from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from core.config import settings


engine = create_async_engine(settings.DATABASE_URL_asyncpg,
                             pool_size=10,
                             max_overflow=20,
                             pool_timeout=30,  # ждать соединение не дольше 30 сек
                             pool_recycle=1800,  # пересоздавать соединения каждые 30 мин
                             pool_pre_ping=True,
                             )

session_factory = async_sessionmaker(engine)