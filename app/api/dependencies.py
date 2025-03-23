from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

# Opzionale: Implementazione di un sistema di API key
# Per un sistema più completo, considerare l'utilizzo di OAuth2

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str] = Depends(API_KEY_HEADER)):
    """
    Verifica l'API key fornita (se la sicurezza è abilitata)
    """
    # In un ambiente di sviluppo, potremmo voler disabilitare l'autenticazione
    if settings.ENVIRONMENT == "development" and not settings.DEBUG:
        return

    # Esempio base di verifica API key
    # In un caso reale, la API key sarebbe verificata contro un database
    valid_api_keys = ["test_api_key"]  # Per test, sostituire con le chiavi valide

    if api_key not in valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key non valida o mancante",
        )
