import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# Crea la base per i modelli SQLAlchemy
Base = declarative_base()

# Crea l'engine SQLAlchemy
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,  # Verifica la connessione prima dell'uso
    connect_args={"check_same_thread": False} if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {},
)

# Crea la factory di sessioni
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    Dependency per ottenere una sessione del database
    Yield una sessione e poi la chiude alla fine dell'uso
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Inizializza il database creando tutti i modelli
    """
    try:
        # Importa tutti i modelli per la loro registrazione
        # pylint: disable=unused-import
        from app.db import models
        
        # Crea le tabelle
        Base.metadata.create_all(bind=engine)
        logger.info("Database inizializzato con successo")
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione del database: {e}")
        raise
