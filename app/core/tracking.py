"""
Modulo per il monitoraggio e l'aggiornamento dei prezzi dei prodotti
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.crawlers.amazon import AmazonCrawler
from app.db import models
from app.core.config import settings
from app.utils.helpers import format_price

logger = logging.getLogger(__name__)


def update_product_prices(db: Session, max_products: int = 50) -> Dict[str, Any]:
    """
    Aggiorna i prezzi dei prodotti in monitoraggio
    Inizia dai prodotti che non sono stati aggiornati da più tempo
    
    Args:
        db: Sessione del database
        max_products: Numero massimo di prodotti da aggiornare in una singola esecuzione
        
    Returns:
        Dizionario con statistiche sull'aggiornamento
    """
    logger.info(f"Avvio aggiornamento prezzi per massimo {max_products} prodotti")
    
    # Recupera i prodotti da aggiornare - quelli con monitoraggio attivo e con l'ultimo aggiornamento più vecchio
    products = db.query(models.Product).join(
        models.TrackingJob, models.Product.id == models.TrackingJob.product_id
    ).filter(
        models.TrackingJob.is_active == True
    ).order_by(
        models.Product.last_checked_at.asc()
    ).limit(max_products).all()
    
    if not products:
        logger.info("Nessun prodotto da aggiornare")
        return {"updated": 0, "failed": 0, "notified": 0}
    
    logger.info(f"Trovati {len(products)} prodotti da aggiornare")
    
    # Statistiche di aggiornamento
    stats = {
        "updated": 0,
        "failed": 0,
        "notified": 0,
        "price_drops": [],
        "back_in_stock": []
    }
    
    with AmazonCrawler(use_cloudscraper=True) as crawler:
        for product in products:
            try:
                logger.info(f"Aggiornamento prodotto {product.asin} - {product.title[:30]}...")
                
                # Aggiorna timestamp anche in caso di errore
                product.last_checked_at = datetime.utcnow()
                
                # Ottieni dettagli aggiornati
                product_details = crawler.get_product_details(url=product.url)
                
                if "error" in product_details:
                    logger.error(f"Errore durante l'aggiornamento di {product.asin}: {product_details['error']}")
                    stats["failed"] += 1
                    continue
                
                # Estrai il prezzo corrente
                current_price_text = product_details["price"]
                current_price_value = format_price(current_price_text)
                
                # Estrai la disponibilità
                current_availability = product_details.get("availability", "")
                was_unavailable = not product.is_available
                now_available = "disponibile" in current_availability.lower() or "disponibile" not in current_availability.lower()
                
                # Controlla se ci sono stati cambiamenti
                price_changed = product.price_text != current_price_text
                availability_changed = was_unavailable and now_available
                
                # Se il prezzo è cambiato, aggiornalo e aggiungi alla cronologia
                if price_changed and current_price_value:
                    # Salva il vecchio prezzo
                    old_price_value = format_price(product.price_text) or 0
                    
                    # Aggiorna il prezzo nel prodotto
                    product.price_text = current_price_text
                    product.price_value = current_price_value
                    
                    # Aggiungi alla cronologia dei prezzi
                    price_history = models.PriceHistory(
                        product_id=product.id,
                        price_text=current_price_text,
                        price_value=current_price_value,
                        timestamp=datetime.utcnow()
                    )
                    db.add(price_history)
                    
                    logger.info(f"Prezzo aggiornato per {product.asin}: {product.price_text} -> {current_price_text}")
                    
                    # Verifica se si tratta di un calo di prezzo
                    if old_price_value and current_price_value < old_price_value:
                        stats["price_drops"].append({
                            "product": product,
                            "old_price": old_price_value,
                            "new_price": current_price_value
                        })
                
                # Se la disponibilità è cambiata, aggiornala
                if availability_changed:
                    product.is_available = True
                    product.availability = current_availability
                    logger.info(f"Disponibilità aggiornata per {product.asin}: Ora disponibile")
                    
                    stats["back_in_stock"].append({
                        "product": product
                    })
                
                # Aggiorna altre informazioni del prodotto
                if product_details.get("rating"):
                    try:
                        rating_text = product_details["rating"]
                        if "su" in rating_text:
                            product.rating = float(rating_text.split("su")[0].strip())
                    except (ValueError, IndexError):
                        pass
                
                # Considera l'aggiornamento completato con successo
                stats["updated"] += 1
                
                # Ritardo per evitare di sovraccaricare Amazon
                time.sleep(settings.REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"Errore nell'aggiornamento del prodotto {product.asin}: {e}")
                stats["failed"] += 1
    
    # Salva le modifiche nel database
    db.commit()
    
    # Gestisci le notifiche
    stats["notified"] = handle_notifications(db, stats["price_drops"], stats["back_in_stock"])
    
    logger.info(f"Aggiornamento prezzi completato. "
                f"Aggiornati: {stats['updated']}, "
                f"Falliti: {stats['failed']}, "
                f"Notifiche inviate: {stats['notified']}")
    
    return stats


def handle_notifications(
    db: Session, 
    price_drops: List[Dict[str, Any]], 
    back_in_stock: List[Dict[str, Any]]
) -> int:
    """
    Gestisce le notifiche per i prodotti con cambiamenti di prezzo o disponibilità
    
    Args:
        db: Sessione del database
        price_drops: Lista di prodotti con calo di prezzo
        back_in_stock: Lista di prodotti tornati disponibili
        
    Returns:
        Numero di notifiche inviate
    """
    notifications_sent = 0
    
    # Gestisci notifiche per cali di prezzo
    for drop in price_drops:
        product = drop["product"]
        
        # Trova i job di tracking per questo prodotto che richiedono notifiche per cali di prezzo
        tracking_jobs = db.query(models.TrackingJob).filter(
            and_(
                models.TrackingJob.product_id == product.id,
                models.TrackingJob.is_active == True,
                models.TrackingJob.notify_on_price_drop == True
            )
        ).all()
        
        for job in tracking_jobs:
            # Se c'è un prezzo target, verifica che sia stato raggiunto
            if job.target_price and drop["new_price"] > job.target_price:
                continue
                
            # Verifica che non sia stata inviata una notifica recente
            should_notify = True
            if job.last_notification_at:
                # Non inviare più di una notifica ogni 24 ore
                if datetime.utcnow() - job.last_notification_at < timedelta(hours=24):
                    should_notify = False
            
            if should_notify:
                # In un'implementazione reale, qui invieresti l'email
                # Per ora, simuliamo l'invio loggando
                logger.info(f"NOTIFICA: Calo di prezzo per '{product.title[:30]}...'. "
                           f"Da {drop['old_price']} a {drop['new_price']}. "
                           f"Target: {job.target_price or 'Nessuno'}. "
                           f"Email: {job.notification_email or 'Non specificata'}")
                
                # Aggiorna il timestamp dell'ultima notifica
                job.last_notification_at = datetime.utcnow()
                notifications_sent += 1
    
    # Gestisci notifiche per prodotti tornati disponibili
    for item in back_in_stock:
        product = item["product"]
        
        # Trova i job di tracking per questo prodotto che richiedono notifiche per disponibilità
        tracking_jobs = db.query(models.TrackingJob).filter(
            and_(
                models.TrackingJob.product_id == product.id,
                models.TrackingJob.is_active == True,
                models.TrackingJob.notify_on_availability == True
            )
        ).all()
        
        for job in tracking_jobs:
            # Verifica che non sia stata inviata una notifica recente
            should_notify = True
            if job.last_notification_at:
                # Non inviare più di una notifica ogni 24 ore
                if datetime.utcnow() - job.last_notification_at < timedelta(hours=24):
                    should_notify = False
            
            if should_notify:
                # In un'implementazione reale, qui invieresti l'email
                # Per ora, simuliamo l'invio loggando
                logger.info(f"NOTIFICA: Prodotto tornato disponibile '{product.title[:30]}...'. "
                           f"Prezzo attuale: {product.price_text}. "
                           f"Email: {job.notification_email or 'Non specificata'}")
                
                # Aggiorna il timestamp dell'ultima notifica
                job.last_notification_at = datetime.utcnow()
                notifications_sent += 1
    
    # Salva le modifiche nel database
    db.commit()
    
    return notifications_sent
