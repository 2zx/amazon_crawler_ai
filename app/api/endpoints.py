import logging
import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.api import models
from app.core.config import settings
from app.crawlers.amazon import AmazonCrawler
from app.utils.helpers import create_error_response

from sqlalchemy.orm import Session
from app.db import models as db_models
from app.core.tracking import update_product_prices
from app.db.session import get_db


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


@router.post(
    "/watchlist/add",
    response_model=models.WatchlistItemResponse,
    responses={400: {"model": models.ErrorResponse}, 500: {"model": models.ErrorResponse}},
    summary="Aggiungi un prodotto alla Watch List",
    description="Aggiungi un prodotto alla Watch List per monitorare prezzo e disponibilità",
    tags=["watchlist"],
)
async def add_to_watchlist(
    watchlist_item: models.WatchlistItemCreate,
    db: Session = Depends(get_db)
):
    try:
        # Controlla se il prodotto esiste già nel database
        product = db.query(db_models.Product).filter(db_models.Product.asin == watchlist_item.asin).first()

        # Se non esiste, aggiungi il prodotto
        if not product:
            # Ottieni dettagli completi del prodotto
            with AmazonCrawler(use_cloudscraper=True) as crawler:
                product_details = crawler.get_product_details(url=str(watchlist_item.url))

                if "error" in product_details:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content=create_error_response(
                            error="Impossibile recuperare i dettagli del prodotto",
                            details=product_details.get("error"),
                        ),
                    )

                # Crea il record del prodotto
                product = db_models.Product(
                    asin=product_details["asin"],
                    title=product_details["title"],
                    url=product_details["url"],
                    price_text=product_details["price"],
                    image_url=product_details["images"][0] if product_details.get("images") else None,
                    category=product_details.get("category"),
                    availability=product_details.get("availability"),
                    description=product_details.get("description")
                )

                # Estrai valutazione numerica se disponibile
                if product_details.get("rating"):
                    try:
                        rating_text = product_details["rating"]
                        # Estrai il numero dalla stringa, es. "4.5 su 5 stelle" -> 4.5
                        if "su" in rating_text:
                            product.rating = float(rating_text.split("su")[0].strip())
                    except (ValueError, IndexError):
                        pass

                db.add(product)
                db.flush()  # Per ottenere l'id generato

                # Aggiungi le specifiche
                if product_details.get("specifications"):
                    for key, value in product_details["specifications"].items():
                        spec = db_models.ProductSpecification(
                            product_id=product.id,
                            key=key,
                            value=value
                        )
                        db.add(spec)

                # Aggiungi le immagini
                if product_details.get("images"):
                    for idx, image_url in enumerate(product_details["images"]):
                        image = db_models.ProductImage(
                            product_id=product.id,
                            url=image_url,
                            position=idx
                        )
                        db.add(image)

                # Registra il prezzo attuale
                price_history = db_models.PriceHistory(
                    product_id=product.id,
                    price_text=product_details["price"]
                )
                db.add(price_history)

        # Crea il job di tracking
        tracking_job = db_models.TrackingJob(
            product_id=product.id,
            name=watchlist_item.name or product.title,
            target_price=watchlist_item.target_price,
            notify_on_availability=watchlist_item.notify_on_availability,
            notify_on_price_drop=watchlist_item.notify_on_price_drop,
            notification_email=watchlist_item.notification_email,
            is_active=True
        )

        db.add(tracking_job)
        db.commit()

        return {
            "id": tracking_job.id,
            "product": {
                "id": product.id,
                "asin": product.asin,
                "title": product.title,
                "url": product.url,
                "price": product.price_text,
                "image_url": product.image_url
            },
            "name": tracking_job.name,
            "target_price": tracking_job.target_price,
            "notify_on_availability": tracking_job.notify_on_availability,
            "notify_on_price_drop": tracking_job.notify_on_price_drop,
            "is_active": tracking_job.is_active,
            "created_at": tracking_job.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Errore durante l'aggiunta alla watch list: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

@router.get(
    "/watchlist",
    response_model=List[models.WatchlistItemResponse],
    responses={500: {"model": models.ErrorResponse}},
    summary="Ottieni la Watch List",
    description="Ottieni l'elenco completo dei prodotti nella Watch List",
    tags=["watchlist"],
)
async def get_watchlist(db: Session = Depends(get_db)):
    try:
        tracking_jobs = db.query(db_models.TrackingJob).join(
            db_models.Product
        ).order_by(
            db_models.TrackingJob.created_at.desc()
        ).all()

        result = []
        for job in tracking_jobs:
            result.append({
                "id": job.id,
                "product": {
                    "id": job.product.id,
                    "asin": job.product.asin,
                    "title": job.product.title,
                    "url": job.product.url,
                    "price": job.product.price_text,
                    "image_url": job.product.image_url
                },
                "name": job.name,
                "target_price": job.target_price,
                "notify_on_availability": job.notify_on_availability,
                "notify_on_price_drop": job.notify_on_price_drop,
                "is_active": job.is_active,
                "created_at": job.created_at.isoformat()
            })

        return result

    except Exception as e:
        logger.error(f"Errore durante il recupero della watch list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

@router.delete(
    "/watchlist/{job_id}",
    response_model=models.SuccessResponse,
    responses={404: {"model": models.ErrorResponse}, 500: {"model": models.ErrorResponse}},
    summary="Rimuovi un prodotto dalla Watch List",
    description="Rimuovi un prodotto dalla Watch List tramite l'ID del job di tracking",
    tags=["watchlist"],
)
async def remove_from_watchlist(job_id: int, db: Session = Depends(get_db)):
    try:
        tracking_job = db.query(db_models.TrackingJob).filter(
            db_models.TrackingJob.id == job_id
        ).first()

        if not tracking_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job di tracking con ID {job_id} non trovato",
            )

        db.delete(tracking_job)
        db.commit()

        return {"success": True, "message": f"Prodotto rimosso dalla Watch List"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante la rimozione dalla watch list: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

@router.put(
    "/watchlist/{job_id}",
    response_model=models.WatchlistItemResponse,
    responses={404: {"model": models.ErrorResponse}, 500: {"model": models.ErrorResponse}},
    summary="Aggiorna un prodotto nella Watch List",
    description="Aggiorna le impostazioni di monitoraggio per un prodotto nella Watch List",
    tags=["watchlist"],
)
async def update_watchlist_item(
    job_id: int,
    update_data: models.WatchlistItemUpdate,
    db: Session = Depends(get_db)
):
    try:
        tracking_job = db.query(db_models.TrackingJob).filter(
            db_models.TrackingJob.id == job_id
        ).first()

        if not tracking_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job di tracking con ID {job_id} non trovato",
            )

        # Aggiorna i campi forniti
        if update_data.name is not None:
            tracking_job.name = update_data.name
        if update_data.target_price is not None:
            tracking_job.target_price = update_data.target_price
        if update_data.notify_on_availability is not None:
            tracking_job.notify_on_availability = update_data.notify_on_availability
        if update_data.notify_on_price_drop is not None:
            tracking_job.notify_on_price_drop = update_data.notify_on_price_drop
        if update_data.is_active is not None:
            tracking_job.is_active = update_data.is_active
        if update_data.notification_email is not None:
            tracking_job.notification_email = update_data.notification_email

        db.commit()

        # Recupera il prodotto associato
        product = db.query(db_models.Product).filter(
            db_models.Product.id == tracking_job.product_id
        ).first()

        return {
            "id": tracking_job.id,
            "product": {
                "id": product.id,
                "asin": product.asin,
                "title": product.title,
                "url": product.url,
                "price": product.price_text,
                "image_url": product.image_url
            },
            "name": tracking_job.name,
            "target_price": tracking_job.target_price,
            "notify_on_availability": tracking_job.notify_on_availability,
            "notify_on_price_drop": tracking_job.notify_on_price_drop,
            "is_active": tracking_job.is_active,
            "created_at": tracking_job.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante l'aggiornamento della watch list: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/watchlist/update-prices",
    response_model=models.PriceUpdateResponse,
    responses={500: {"model": models.ErrorResponse}},
    summary="Aggiorna i prezzi dei prodotti nella Watch List",
    description="Avvia un aggiornamento manuale dei prezzi per i prodotti nella Watch List",
    tags=["watchlist"],
)
async def update_prices(
    limit: int = Query(10, ge=1, le=50, description="Numero massimo di prodotti da aggiornare"),
    db: Session = Depends(get_db)
):
    try:
        # Esegui l'aggiornamento dei prezzi
        stats = update_product_prices(db, max_products=limit)

        return {
            "success": True,
            "products_updated": stats["updated"],
            "products_failed": stats["failed"],
            "notifications_sent": stats["notified"],
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Errore durante l'aggiornamento manuale dei prezzi: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

# Aggiungi questo endpoint alla fine del file

@router.get(
    "/product/{product_id}/price-history",
    response_model=List[models.PriceHistoryEntry],
    responses={404: {"model": models.ErrorResponse}, 500: {"model": models.ErrorResponse}},
    summary="Ottieni lo storico dei prezzi di un prodotto",
    description="Restituisce lo storico completo dei prezzi di un prodotto",
    tags=["products"],
)
async def get_price_history(product_id: int, db: Session = Depends(get_db)):
    try:
        # Verifica che il prodotto esista
        product = db.query(db_models.Product).filter(db_models.Product.id == product_id).first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prodotto con ID {product_id} non trovato",
            )

        # Recupera lo storico dei prezzi
        price_history = db.query(db_models.PriceHistory).filter(
            db_models.PriceHistory.product_id == product_id
        ).order_by(
            db_models.PriceHistory.timestamp.asc()
        ).all()

        # Formatta i risultati
        result = []
        for entry in price_history:
            result.append({
                "id": entry.id,
                "price_text": entry.price_text,
                "price_value": entry.price_value,
                "timestamp": entry.timestamp.isoformat()
            })

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante il recupero dello storico prezzi: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
