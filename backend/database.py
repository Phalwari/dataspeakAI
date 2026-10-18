import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

raw_db_url = os.getenv("DATABASE_URL")
if not raw_db_url or raw_db_url == "sqlite:///./app.db":
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    default_db = os.path.join(backend_dir, "app.db").replace("\\", "/")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{default_db}"
else:
    SQLALCHEMY_DATABASE_URL = raw_db_url

# For SQLite, we need connect_args={"check_same_thread": False}
# For PostgreSQL (production), we don't.
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine_kwargs = {"connect_args": connect_args}
    if ":memory:" in SQLALCHEMY_DATABASE_URL:
        from sqlalchemy.pool import StaticPool
        engine_kwargs["poolclass"] = StaticPool
    engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
