from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.endpoints import router as api_router
from app.core.config import settings
from app.core.logging import configure_logging

# Configura il logging
configure_logging()

# Crea l'applicazione FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware per reindirizzare a Streamlit (in produzione)
class StreamlitRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/streamlit" or request.url.path.startswith("/streamlit/"):
            # In produzione, reindirizza alla porta 8501 interna
            # Cloud Run gestirà il proxy dalla porta 8080
            return RedirectResponse(url=f"http://localhost:8501{request.url.path}")
        return await call_next(request)

# Aggiungi middleware solo in produzione
if settings.ENVIRONMENT == "production":
    app.add_middleware(StreamlitRedirectMiddleware)

# Includi i router API
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", include_in_schema=False)
async def root():
    """
    Reindirizza alla documentazione API di default
    """
    return RedirectResponse(url=settings.DOCS_URL)

@app.get("/health", tags=["health"])
async def health_check():
    """
    Endpoint di health check per Google Cloud Run
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
