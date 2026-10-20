from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    tinyfish_api_key: str = ""
    tinyfish_base_url: str = "https://agent.tinyfish.ai"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    public_base_url: str = "http://localhost:8000"
    frontend_origins: str = "http://localhost:3000,http://localhost:5173"

    live_weather: bool = False
    live_filing: bool = True

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()
