
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Config:
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY")

    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is missing from .env")

    # Database settings
    DB_HOST = os.getenv("DB_HOST", "")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "examdesk")

    # Database type: SQLite or MySQL/RDS
    DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

    if DB_TYPE not in ("sqlite", "mysql"):
        raise RuntimeError(
            "DB_TYPE must be either 'sqlite' or 'mysql'"
        )

    # Local SQLite database path
    SQLITE_PATH = os.getenv(
        "SQLITE_PATH",
        str(BASE_DIR / "database" / "examdesk.db")
    )

    # Token settings
    TOKEN_EXPIRATION_SECONDS = int(
        os.getenv("TOKEN_EXPIRATION_SECONDS", "86400")
    )

    # AWS settings
    AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
    AWS_SES_SENDER = os.getenv("AWS_SES_SENDER", "")
    S3_BUCKET = os.getenv("S3_BUCKET", "")
