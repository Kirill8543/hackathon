from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000

class ApiPrefix(BaseModel):
    prefix: str = "/api"

class Settings(BaseSettings):

    Vk_MAX_API_URL: str = "https://api.vk-max.example.com"
    VK_MAX_TOKEN: str

    run: RunConfig = RunConfig()
    api: ApiPrefix = ApiPrefix()

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    @property
    def DATABASE_URL_asyncpg(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file="core/settings.env")


settings = Settings()
