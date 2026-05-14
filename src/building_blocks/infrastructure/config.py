from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvConfig(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # --- Cấu hình Bảo mật ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- Cấu hình App ---
    APP_NAME: str 
    DEBUG: bool 
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Đọc từ file .env
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore" 
    )


envConfig = EnvConfig()
