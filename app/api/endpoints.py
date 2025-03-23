import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api import models
from app.core.config import settings
from app.crawlers.amazon import AmazonCrawler
from app.utils.helpers import create_error_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search",
    response_model=models.SearchResponse,
    responses={400: {"model": models.ErrorResponse}, 500: {"model": models.ErrorResponse}},
    summary="Ricerca prodotti su Amazon",
    description="Effettua una ricerca di prodotti su Amazon in base alla query fornita",
    tags=["products"],
)
async def search_products(search_query: models.SearchQuery):
    try:
        with AmazonCrawler(use_cloudscraper=search_query.use_cloudscraper) as crawler:
            products = crawler.search_products(
                query=search_query.query,
                max_products=search_query.max_products,
            )

        return {
            "query": search_query.query,
            "products": products,
            "count": len(products),
        }
    except Exception as e:
        logger.error(f"Errore durante la ricerca dei prodotti: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/product/details",
    response_model=models.ProductDetailResponse,
    responses={400: {"model": models.ErrorResponse}, 500: {"model": models.ErrorResponse}},
    summary="Ottieni dettagli di un prodotto Amazon",
    description="Ottieni informazioni dettagliate su un prodotto Amazon dall'URL",
    tags=["products"],
)
async def get_product_details(query: models.ProductDetailQuery):
    try:
        with AmazonCrawler(use_cloudscraper=query.use_cloudscraper) as crawler:
            product_details = crawler.get_product_details(url=str(query.url))

        if "error" in product_details:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=create_error_response(
                    error="Impossibile recuperare i dettagli del prodotto",
                    details=product_details.get("error"),
                ),
            )

        return {
            "product": product_details,
        }
    except Exception as e:
        logger.error(f"Errore durante il recupero dei dettagli del prodotto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/version",
    summary="Informazioni sulla versione",
    description="Restituisce informazioni sulla versione dell'API",
    tags=["info"],
)
async def get_version():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.PROJECT_DESCRIPTION,
    }
