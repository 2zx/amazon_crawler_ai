from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl


class ProductBase(BaseModel):
    """
    Modello base per i prodotti
    """
    asin: str = Field(..., description="Amazon Standard Identification Number")
    title: str = Field(..., description="Titolo del prodotto")
    url: str = Field(..., description="URL del prodotto su Amazon")
    price: str = Field(..., description="Prezzo del prodotto (formato testuale)")
    image_url: Optional[str] = Field(None, description="URL dell'immagine del prodotto")
    rating: Optional[str] = Field(None, description="Valutazione del prodotto")
    reviews: Optional[str] = Field(None, description="Numero di recensioni")


class ProductSearchResult(ProductBase):
    """
    Modello per i risultati di ricerca prodotti
    """
    timestamp: float = Field(..., description="Timestamp dell'estrazione")


class ProductDetail(ProductBase):
    """
    Modello per i dettagli completi di un prodotto
    """
    description: Optional[str] = Field(None, description="Descrizione del prodotto")
    specifications: Dict[str, str] = Field(default_factory=dict, description="Specifiche tecniche del prodotto")
    images: List[str] = Field(default_factory=list, description="Elenco di URL di immagini del prodotto")
    availability: Optional[str] = Field(None, description="Disponibilità del prodotto")
    category: Optional[str] = Field(None, description="Categoria del prodotto")
    related_products: List[Dict[str, Any]] = Field(default_factory=list, description="Prodotti correlati")
    timestamp: float = Field(..., description="Timestamp dell'estrazione")


class SearchQuery(BaseModel):
    """
    Modello per la richiesta di ricerca prodotti
    """
    query: str = Field(..., description="Query di ricerca")
    max_products: int = Field(20, description="Numero massimo di prodotti da restituire", ge=1, le=100)
    use_cloudscraper: bool = Field(True, description="Utilizza CloudScraper per bypassare protezioni anti-bot")


class ProductDetailQuery(BaseModel):
    """
    Modello per la richiesta di dettagli prodotto
    """
    url: str = Field(..., description="URL del prodotto su Amazon")
    use_cloudscraper: bool = Field(True, description="Utilizza CloudScraper per bypassare protezioni anti-bot")


class SearchResponse(BaseModel):
    """
    Modello per la risposta di ricerca prodotti
    """
    query: str = Field(..., description="Query di ricerca utilizzata")
    products: List[ProductSearchResult] = Field(..., description="Elenco dei prodotti trovati")
    count: int = Field(..., description="Numero di prodotti trovati")


class ProductDetailResponse(BaseModel):
    """
    Modello per la risposta di dettagli prodotto
    """
    product: ProductDetail = Field(..., description="Dettagli del prodotto")


class ErrorResponse(BaseModel):
    """
    Modello per le risposte di errore
    """
    error: str = Field(..., description="Messaggio di errore")
    details: Optional[str] = Field(None, description="Dettagli dell'errore")


class HealthResponse(BaseModel):
    """
    Modello per la risposta di health check
    """
    status: str = Field(..., description="Stato del servizio")
    version: str = Field(..., description="Versione dell'API")


class ProductSummary(BaseModel):
    """
    Modello per il riepilogo di un prodotto nella Watch List
    """
    id: int = Field(..., description="ID del prodotto nel database")
    asin: str = Field(..., description="Amazon Standard Identification Number")
    title: str = Field(..., description="Titolo del prodotto")
    url: str = Field(..., description="URL del prodotto su Amazon")
    price: str = Field(..., description="Prezzo del prodotto (formato testuale)")
    image_url: Optional[str] = Field(None, description="URL dell'immagine del prodotto")


class WatchlistItemCreate(BaseModel):
    """
    Modello per la creazione di un elemento nella Watch List
    """
    asin: Optional[str] = Field(None, description="ASIN del prodotto")
    url: str = Field(..., description="URL del prodotto su Amazon")
    name: Optional[str] = Field(None, description="Nome personalizzato per il monitoraggio")
    target_price: Optional[float] = Field(None, description="Prezzo target per le notifiche")
    notify_on_availability: bool = Field(False, description="Notifica quando il prodotto è disponibile")
    notify_on_price_drop: bool = Field(True, description="Notifica quando il prezzo scende")
    notification_email: Optional[str] = Field(None, description="Email per le notifiche")


class WatchlistItemUpdate(BaseModel):
    """
    Modello per l'aggiornamento di un elemento nella Watch List
    """
    name: Optional[str] = Field(None, description="Nome personalizzato per il monitoraggio")
    target_price: Optional[float] = Field(None, description="Prezzo target per le notifiche")
    notify_on_availability: Optional[bool] = Field(None, description="Notifica quando il prodotto è disponibile")
    notify_on_price_drop: Optional[bool] = Field(None, description="Notifica quando il prezzo scende")
    is_active: Optional[bool] = Field(None, description="Stato attivo del monitoraggio")
    notification_email: Optional[str] = Field(None, description="Email per le notifiche")


class WatchlistItemResponse(BaseModel):
    """
    Modello per la risposta di un elemento nella Watch List
    """
    id: int = Field(..., description="ID del job di tracking")
    product: ProductSummary = Field(..., description="Dettagli del prodotto")
    name: str = Field(..., description="Nome del monitoraggio")
    target_price: Optional[float] = Field(None, description="Prezzo target per le notifiche")
    notify_on_availability: bool = Field(..., description="Notifica quando il prodotto è disponibile")
    notify_on_price_drop: bool = Field(..., description="Notifica quando il prezzo scende")
    is_active: bool = Field(..., description="Stato attivo del monitoraggio")
    created_at: str = Field(..., description="Data e ora di creazione")


class SuccessResponse(BaseModel):
    """
    Modello per le risposte di successo generiche
    """
    success: bool = Field(..., description="Indicatore di successo dell'operazione")
    message: Optional[str] = Field(None, description="Messaggio informativo")


class PriceUpdateResponse(BaseModel):
    """
    Modello per la risposta di aggiornamento prezzi
    """
    success: bool = Field(..., description="Indicatore di successo dell'operazione")
    products_updated: int = Field(..., description="Numero di prodotti aggiornati con successo")
    products_failed: int = Field(..., description="Numero di prodotti con aggiornamento fallito")
    notifications_sent: int = Field(..., description="Numero di notifiche inviate")
    timestamp: str = Field(..., description="Timestamp dell'aggiornamento")


class PriceHistoryEntry(BaseModel):
    """
    Modello per una voce dello storico prezzi
    """
    id: int = Field(..., description="ID dell'entry nella cronologia")
    price_text: str = Field(..., description="Prezzo in formato testuale")
    price_value: Optional[float] = Field(None, description="Prezzo in formato numerico")
    timestamp: str = Field(..., description="Timestamp della rilevazione")
