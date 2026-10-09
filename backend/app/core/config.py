import json
import os
from pathlib import Path
from typing import List, Union
from dotenv import load_dotenv

# Locate and load the .env file
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "ToolShoppe ERP Backend")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "toolshoppe_super_secret_jwt_key_change_in_production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:root@localhost:3306/toolshoppe?charset=utf8mb4"
    )
    FALLBACK_TO_SQLITE: bool = os.getenv("FALLBACK_TO_SQLITE", "True").lower() in ("true", "1", "yes")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./toolshoppe.db")

    # CORS Configuration
    _cors_raw = os.getenv("CORS_ORIGINS", '["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://localhost:8000"]')
    try:
        CORS_ORIGINS: List[str] = json.loads(_cors_raw)
    except Exception:
        CORS_ORIGINS: List[str] = [origin.strip() for origin in _cors_raw.split(",") if origin.strip()]

    # Email SMTP Configuration
    SMTP_ENABLED: bool = os.getenv("SMTP_ENABLED", "True").lower() in ("true", "1", "yes")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "tdevendiran123@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "ToolShoppe Industrial Supply")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "tdevendiran123@gmail.com")


settings = Settings()
