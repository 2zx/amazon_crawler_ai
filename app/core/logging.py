import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Formattatore di log in formato JSON per Google Cloud Logging
    """

    def format(self, record: logging.LogRecord) -> str:
        log_dict: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Aggiungi eventuali eccezioni
        if record.exc_info:
            log_dict["exception"] = self.formatException(record.exc_info)

        # Aggiungi eventuali attributi extra
        if hasattr(record, "extra"):
            log_dict["extra"] = record.extra

        return json.dumps(log_dict)


def configure_logging() -> None:
    """
    Configura il logging dell'applicazione
    """
    # Rimuovi gli handler esistenti
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Imposta il livello di logging in base all'ambiente
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    root_logger.setLevel(log_level)

    # Crea l'handler per lo stdout
    handler = logging.StreamHandler(sys.stdout)

    # Usa il formattatore JSON in produzione, altrimenti usa un formato standard
    if settings.ENVIRONMENT == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )

    # Aggiungi l'handler al logger root
    root_logger.addHandler(handler)

    # Imposta il livello di logging per librerie di terze parti
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
