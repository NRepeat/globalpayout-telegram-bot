from pydantic.v1 import BaseSettings

__version__ = "dev"


class Settings(BaseSettings):
    # Backend api connection
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    TRANSACTION_API_SECRET: str = ""

    EXCHANGE_API_KEY: str = ""
    EXCHANGE_SECRET_KEY: str = ""
    EXCHANGE_BASE_URL: str = "https://www.globalpayout.club/service/api/v1/"

    # aiogram settings
    WEBHOOK_HOST: str = ""

    ADMINS_ID: list[int] = []

    # FastAPI settings
    BASE_URL: str = ""
    SERVER_PORT: str = "2000"
    SERVER_ADDRESS: str = "0.0.0.0"
    LOCAL_BOT_API: str = ""
    USE_LOCAL_BOT_API: bool = False

    # Database settings
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_HOST: str = ""
    DB_PORT: int = 0
    DB_NAME: str = ""

    FASTAPI_BASE_PATH: str = ""

    TIME_ZONE: str = "UTC"

    # Rates autoposting (ARG-58). 0 disables posting.
    # In this chat all bot commands are ignored — only the cron posts.
    RATES_POSTING_CHAT_ID: int = -1004310943335

    class Config:
        env_file = ".env"


settings = Settings()
