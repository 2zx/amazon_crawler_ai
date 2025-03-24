"""
Modulo per la gestione delle attività pianificate
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.tracking import update_product_prices

logger = logging.getLogger(__name__)


class SchedulerThread(threading.Thread):
    """
    Thread che esegue le attività pianificate periodicamente
    """
    
    def __init__(self, interval_minutes: int = 60):
        """
        Inizializza il thread scheduler
        
        Args:
            interval_minutes: Intervallo in minuti tra le esecuzioni
        """
        super().__init__(daemon=True)
        self.interval_minutes = interval_minutes
        self.stop_event = threading.Event()
        self.last_run = None
        
        logger.info(f"Scheduler inizializzato con intervallo di {interval_minutes} minuti")
    
    def run(self):
        """
        Esegue le attività pianificate a intervalli regolari
        """
        logger.info("Scheduler avviato")
        
        while not self.stop_event.is_set():
            # Controlla se è tempo di eseguire le attività
            current_time = datetime.now()
            
            if self.last_run is None or (current_time - self.last_run) >= timedelta(minutes=self.interval_minutes):
                logger.info("Avvio esecuzione attività pianificate")
                
                try:
                    # Crea una nuova sessione del database
                    db = SessionLocal()
                    
                    # Esegui l'aggiornamento dei prezzi
                    stats = update_product_prices(db, max_products=20)
                    
                    logger.info(f"Attività pianificate completate. "
                                f"Prodotti aggiornati: {stats['updated']}, "
                                f"Falliti: {stats['failed']}, "
                                f"Notifiche inviate: {stats['notified']}")
                    
                except Exception as e:
                    logger.error(f"Errore durante l'esecuzione delle attività pianificate: {e}")
                
                finally:
                    # Chiudi la sessione del database
                    db.close()
                
                # Aggiorna il timestamp dell'ultima esecuzione
                self.last_run = current_time
            
            # Attendi per un breve periodo prima di controllare nuovamente
            # Usiamo un breve timeout per consentire una terminazione pulita
            self.stop_event.wait(timeout=60)  # Controlla ogni minuto
    
    def stop(self):
        """
        Interrompe il thread dello scheduler
        """
        logger.info("Arresto dello scheduler")
        self.stop_event.set()


# Funzione di utilità per avviare lo scheduler
def start_scheduler(interval_minutes: int = 60) -> SchedulerThread:
    """
    Avvia lo scheduler delle attività pianificate
    
    Args:
        interval_minutes: Intervallo in minuti tra le esecuzioni
        
    Returns:
        L'istanza del thread scheduler
    """
    scheduler = SchedulerThread(interval_minutes=interval_minutes)
    scheduler.start()
    return scheduler
