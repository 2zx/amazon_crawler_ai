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
