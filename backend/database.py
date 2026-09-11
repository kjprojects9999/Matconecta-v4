from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurada. Defina DATABASE_URL no ambiente ou no arquivo .env.")

# Railway/MySQL providers may expose mysql:// while this project intentionally
# uses PyMySQL. Normalize compatible MySQL/MariaDB URLs to the installed driver.
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = "mysql+pymysql://" + DATABASE_URL[len("mysql://"): ]
elif DATABASE_URL.startswith("mysql+mysqlconnector://"):
    DATABASE_URL = "mysql+pymysql://" + DATABASE_URL[len("mysql+mysqlconnector://"): ]

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}
if DATABASE_URL.startswith(("mysql://", "mysql+pymysql://", "mysql+mysqlconnector://", "mariadb://", "mariadb+pymysql://")):
    engine_kwargs.update(pool_size=10, max_overflow=20, connect_args={"connect_timeout": 8})

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def db_ping() -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

def init_db() -> None:
    from models import Assunto, FundamentoTopico, Questao, Resposta, Sessao, Tentativa, Usuario
    _ = (Assunto, FundamentoTopico, Questao, Resposta, Sessao, Tentativa, Usuario)
    Base.metadata.create_all(engine)
