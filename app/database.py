from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.config import get_settings
from app.models import Base

settings = get_settings()
_is_sqlite = settings.database_url.startswith("sqlite")

# Render provides a standard postgres URL. We just need to ensure SSL is on.
connect_args = {}
if _is_sqlite:
    connect_args = {"check_same_thread": False}
elif "postgresql" in settings.database_url:
    connect_args = {"sslmode": "require"}

engine = create_engine(
    settings.database_url, 
    connect_args=connect_args, 
    pool_pre_ping=True
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    Base.metadata.create_all(bind=engine)