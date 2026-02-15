from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tracemyride:tracemyride@db:5432/tracemyride"
    valhalla_url: str = "http://valhalla:8002"
    elevation_url: str = "http://elevation:5000"

    model_config = {"env_file": ".env"}


settings = Settings()
