from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from core.config import settings


engine = create_async_engine(settings.DATABASE_URL_asyncpg,
                             # echo=True,
                             )

session_factory = async_sessionmaker(engine)