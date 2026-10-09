import logging
import socket
from pathlib import Path
from typing import Generator
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger("app.db")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


_MYSQL_CHECK_CACHE = None


def is_mysql_reachable(url_str: str, timeout: float = 0.8) -> bool:
    """Fast socket test to check if remote MySQL host and port are responding."""
    global _MYSQL_CHECK_CACHE
    if _MYSQL_CHECK_CACHE is not None:
        return _MYSQL_CHECK_CACHE

    try:
        clean = url_str.replace("mysql+pymysql://", "http://").replace("mysql://", "http://")
        parsed = urlparse(clean)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 3306
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            _MYSQL_CHECK_CACHE = True
            return True
    except Exception:
        _MYSQL_CHECK_CACHE = False
        return False


def get_sqlite_url() -> str:
    path = Path(settings.SQLITE_DB_PATH)
    if not path.is_absolute():
        path = BACKEND_DIR / path.name
    return f"sqlite:///{path.as_posix()}"


def create_db_engine():
    """
    Initialize database engine.
    Uses MySQL if host is reachable; otherwise immediately falls back to local SQLite.
    """
    db_url = settings.DATABASE_URL
    if db_url.startswith("mysql"):
        if is_mysql_reachable(db_url, timeout=5.0):
            try:
                engine = create_engine(
                    db_url,
                    pool_pre_ping=True,
                    pool_recycle=60,
                    pool_size=10,
                    max_overflow=20,
                    connect_args={"connect_timeout": 15, "read_timeout": 120, "write_timeout": 120}
                )
                with engine.connect() as conn:
                    pass
                logger.info("Successfully connected to MySQL database.")
                return engine
            except Exception as exc:
                logger.warning(f"MySQL handshake failed: {exc}")
        else:
            logger.warning(f"MySQL server at {db_url} is unreachable or offline.")

    if settings.FALLBACK_TO_SQLITE:
        sqlite_url = get_sqlite_url()
        logger.info(f"Using local SQLite database: {sqlite_url}")
        eng = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False, "timeout": 30},
            poolclass=NullPool
        )
        from sqlalchemy import event
        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=15000")
            cursor.close()
        return eng

    raise RuntimeError("Primary database unreachable and fallback is disabled.")


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
