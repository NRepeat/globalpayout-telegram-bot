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

    # Сервис сверки P2P-ордеров (exchange-check): общий для всех ботов,
    # атомарно резервирует ордер за заявкой. Пустой секрет = dev-режим сервиса.
    EXCHANGE_CHECK_URL: str = "http://localhost:8090"
    EXCHANGE_CHECK_SECRET: str = ""

    # Бухгалтеры: только им разрешён ручной ввод курса при закрытии заявки.
    # В env — id через запятую ("123,456"), как в других ботах; поэтому поле
    # строковое: list[int] pydantic парсил бы из env как JSON и падал бы.
    BOOKKEEPER_TG_IDS: str = ""

    @property
    def bookkeeper_ids(self) -> frozenset[int]:
        # мусор и пробелы молча пропускаем: гард должен запрещать, а не падать
        return frozenset(
            int(x)
            for x in (part.strip() for part in self.BOOKKEEPER_TG_IDS.split(","))
            if x.isdigit()
        )

    class Config:
        env_file = ".env"


settings = Settings()
