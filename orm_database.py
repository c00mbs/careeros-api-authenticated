"""Engine and session factory for the SQLAlchemy models."""

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from modules.models import Base


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///careeros.db")


def create_database_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite:") else {}
    return create_engine(database_url, connect_args=connect_args)


engine = create_database_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_orm_database(database_engine: Engine = engine) -> None:
    """Create missing tables, including auth_credentials on existing databases."""
    Base.metadata.create_all(bind=database_engine)
