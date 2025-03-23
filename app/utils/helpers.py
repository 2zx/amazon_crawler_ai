import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def is_valid_amazon_url(url: str) -> bool:
    """
    Verifica se un URL è un URL Amazon valido
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        # Verifica che il dominio sia di Amazon
        valid_domains = [
            "amazon.com",
            "amazon.it",
            "amazon.co.uk",
            "amazon.de",
            "amazon.fr",
            "amazon.es",
            "amazon.co.jp",
            "amazon.ca",
            "amazon.in",
            "amazon.com.au",
            "amazon.com.br",
            "amazon.nl",
            "amazon.mx",
            "amazon.cn",
            "amazon.se",
            "amazon.pl",
            "amazon.sa",
            "amazon.sg",
            "amazon.ae",
            "amazon.com.tr",
        ]

        # Verifica che il dominio sia in un formato Amazon valido
        is_amazon_domain = False
        for valid_domain in valid_domains:
            if domain.endswith(valid_domain):
                is_amazon_domain = True
                break

        # Verifica che sia presente un percorso
        has_path = bool(parsed_url.path)

        return is_amazon_domain and has_path

    except Exception:
        return False


def extract_asin_from_url(url: str) -> Optional[str]:
    """
    Estrae l'ASIN da un URL Amazon
    """
    try:
        # Formato /dp/ASIN/
        if "/dp/" in url:
            asin = url.split("/dp/")[1].split("/")[0].split("?")[0]
            return asin

        # Formato /gp/product/ASIN/
        elif "/gp/product/" in url:
            asin = url.split("/gp/product/")[1].split("/")[0].split("?")[0]
            return asin

        # Formato /exec/obidos/asin/ASIN/
        elif "/exec/obidos/asin/" in url:
            asin = url.split("/exec/obidos/asin/")[1].split("/")[0].split("?")[0]
            return asin

        # Cercando il parametro ASIN nell'URL
        elif "ASIN=" in url:
            asin = url.split("ASIN=")[1].split("&")[0]
            return asin

        return None

    except Exception:
        return None


def format_price(price_text: str) -> Optional[float]:
    """
    Formatta una stringa di prezzo in un valore float
    """
    try:
        # Rimuovi tutti i caratteri non numerici tranne il punto decimale
        digits_only = ''.join(c for c in price_text if c.isdigit() or c == '.' or c == ',')

        # Sostituisci la virgola con il punto (standard europeo)
        digits_only = digits_only.replace(',', '.')

        # Se ci sono più punti decimali, tieni solo l'ultimo
        if digits_only.count('.') > 1:
            parts = digits_only.split('.')
            digits_only = ''.join(parts[:-1]) + '.' + parts[-1]

        # Converti in float
        return float(digits_only)

    except Exception:
        return None


def create_error_response(error: str, details: Optional[str] = None) -> Dict[str, Any]:
    """
    Crea una risposta di errore standardizzata
    """
    response = {"error": error}

    if details:
        response["details"] = details

    return response


def save_to_json(data: Union[List[Any], Dict[str, Any]], filename: str) -> bool:
    """
    Salva dati in un file JSON
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Errore durante il salvataggio del file JSON {filename}: {e}")
        return False


def load_from_json(filename: str) -> Optional[Union[List[Any], Dict[str, Any]]]:
    """
    Carica dati da un file JSON
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Errore durante il caricamento del file JSON {filename}: {e}")
        return None


def get_current_timestamp() -> float:
    """
    Restituisce il timestamp Unix corrente
    """
    return datetime.now().timestamp()


def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Formatta un timestamp Unix in una stringa leggibile
    """
    return datetime.fromtimestamp(timestamp).strftime(format_str)
