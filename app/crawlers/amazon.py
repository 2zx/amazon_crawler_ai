import logging
import random
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, quote_plus

import requests
import cloudscraper
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from app.core.config import settings
from app.utils.helpers import is_valid_amazon_url, extract_asin_from_url

logger = logging.getLogger(__name__)


class AmazonCrawler:
    """
    Crawler per Amazon basato su requests e BeautifulSoup
    Con supporto per cloudscraper per bypassare eventuali protezioni anti-bot
    """

    def __init__(
        self,
        proxy: Optional[str] = None,
        use_cloudscraper: bool = True,
    ):
        self.base_url = settings.AMAZON_BASE_URL
        self.proxy = proxy or settings.PROXY_URL if settings.USE_PROXY else None
        self.use_cloudscraper = use_cloudscraper

        if use_cloudscraper:
            self.session = self._create_cloudscraper_session()
        else:
            self.session = self._create_requests_session()

    def _create_requests_session(self) -> requests.Session:
        """
        Crea una sessione requests con User-Agent e proxy se configurati
        """
        session = requests.Session()

        # Configura User-Agent
        if settings.USER_AGENT_ROTATION:
            try:
                user_agent = UserAgent().random
            except Exception:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        else:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

        session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        })

        # Configura proxy se necessario
        if self.proxy:
            session.proxies.update({
                "http": self.proxy,
                "https": self.proxy,
            })

        return session

    def _create_cloudscraper_session(self) -> cloudscraper.CloudScraper:
        """
        Crea una sessione cloudscraper per bypassare protezioni anti-bot
        """
        # Configura User-Agent
        if settings.USER_AGENT_ROTATION:
            try:
                user_agent = UserAgent().random
            except Exception:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        else:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

        # Crea la sessione CloudScraper
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
                'mobile': False,
            },
            delay=settings.REQUEST_DELAY,
            interpreter='js2py',  # Utilizza js2py come interprete JavaScript
            allow_brotli=True,    # Supporta la compressione Brotli
        )

        # Aggiunge intestazioni personalizzate
        scraper.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        })

        # Configura proxy se necessario
        if self.proxy:
            scraper.proxies.update({
                "http": self.proxy,
                "https": self.proxy,
            })

        return scraper

    def search_products(self, query: str, max_products: int = 20) -> List[Dict[str, Any]]:
        """
        Cerca prodotti su Amazon in base alla query fornita
        """
        search_url = urljoin(self.base_url, f"/s?k={quote_plus(query)}")
        logger.info(f"Ricerca prodotti con query: {query}")

        products = []
        page = 1

        while len(products) < max_products:
            page_url = f"{search_url}&page={page}"
            logger.debug(f"Crawling page: {page_url}")

            # Aggiunta di un ritardo tra le richieste per evitare il blocco
            time.sleep(settings.REQUEST_DELAY * (1 + random.random()))

            try:
                page_products = self._extract_products(page_url)

                if not page_products:
                    logger.warning(f"Nessun prodotto trovato sulla pagina {page}")
                    break

                products.extend(page_products)

                # Passa alla pagina successiva
                page += 1

                # Limita il numero massimo di pagine da crawlare
                if page > 5:
                    logger.info("Raggiunto il limite massimo di pagine")
                    break

            except Exception as e:
                logger.error(f"Errore durante il crawling della pagina {page}: {e}")
                break

        # Tronca l'elenco dei prodotti al numero massimo richiesto
        return products[:max_products]

    def _extract_products(self, url: str) -> List[Dict[str, Any]]:
        """
        Estrae i prodotti da una pagina di ricerca utilizzando requests/cloudscraper e BeautifulSoup
        """
        try:
            response = self.session.get(url, timeout=settings.REQUEST_TIMEOUT)

            if response.status_code != 200:
                logger.warning(f"Stato della risposta non valido: {response.status_code}")
                return []

            return self._parse_search_results(response.text)
        except Exception as e:
            logger.error(f"Errore durante l'estrazione dei prodotti: {e}")
            return []

    def _parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Analizza il contenuto HTML di una pagina di risultati di ricerca Amazon
        """
        soup = BeautifulSoup(html_content, "lxml")
        products = []

        # Cerca tutti gli elementi prodotto nella pagina
        product_elements = soup.select("div.s-result-item[data-asin]:not([data-asin=''])") or soup.select("div.sg-col[data-asin]:not([data-asin=''])")

        for element in product_elements:
            try:
                # Estrai ASIN (Amazon Standard Identification Number)
                asin = element.get("data-asin")

                if not asin:
                    continue

                # Estrai il titolo del prodotto
                title_element = element.select_one("h2 a span") or element.select_one("h5 a") or element.select_one(".a-size-medium.a-color-base.a-text-normal")
                title = title_element.text.strip() if title_element else "Titolo non disponibile"

                # Estrai l'URL del prodotto
                link_element = element.select_one("h2 a") or element.select_one("h5 a")
                link = urljoin(self.base_url, link_element.get("href")) if link_element else None

                # Estrai il prezzo
                price_element = element.select_one(".a-price .a-offscreen") or element.select_one(".a-price")
                price = price_element.text.strip() if price_element else "Prezzo non disponibile"

                # Estrai l'immagine
                img_element = element.select_one("img.s-image") or element.select_one("img.a-dynamic-image")
                img_url = img_element.get("src") if img_element else None

                # Estrai le recensioni
                rating_element = element.select_one("i.a-icon-star-small") or element.select_one("i.a-icon-star")
                rating_text = rating_element.text.strip() if rating_element else "Valutazione non disponibile"

                # Estrai il numero di recensioni
                reviews_element = element.select_one("span.a-size-base.s-underline-text") or element.select_one("a.a-link-normal span.a-size-base")
                reviews = reviews_element.text.strip() if reviews_element else "0"

                product = {
                    "asin": asin,
                    "title": title,
                    "url": link,
                    "price": price,
                    "image_url": img_url,
                    "rating": rating_text,
                    "reviews": reviews,
                    "timestamp": time.time(),
                }

                products.append(product)

            except Exception as e:
                logger.error(f"Errore durante l'analisi di un elemento prodotto: {e}")
                continue

        logger.info(f"Estratti {len(products)} prodotti dalla pagina")
        return products

    def get_product_details(self, url: str) -> Dict[str, Any]:
        """
        Ottiene dettagli completi di un prodotto Amazon dall'URL
        """
        logger.info(f"Recupero dettagli del prodotto: {url}")

        # Aggiungi un ritardo per evitare il blocco
        time.sleep(settings.REQUEST_DELAY * (1 + random.random()))

        try:
            return self._extract_product_details(url)
        except Exception as e:
            logger.error(f"Errore durante l'estrazione dei dettagli del prodotto: {e}")
            return {"error": str(e)}

    def _extract_product_details(self, url: str) -> Dict[str, Any]:
        """
        Estrae i dettagli del prodotto utilizzando requests/cloudscraper e BeautifulSoup
        """
        try:
            response = self.session.get(url, timeout=settings.REQUEST_TIMEOUT)

            if response.status_code != 200:
                logger.warning(f"Stato della risposta non valido: {response.status_code}")
                return {"error": f"Stato della risposta: {response.status_code}"}

            return self._parse_product_details(response.text, url)
        except Exception as e:
            logger.error(f"Errore durante l'estrazione dei dettagli del prodotto: {e}")
            return {"error": str(e)}

    def _parse_product_details(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Analizza il contenuto HTML di una pagina di dettaglio prodotto Amazon
        """
        soup = BeautifulSoup(html_content, "lxml")

        # Estrai ASIN dall'URL o dalla pagina
        asin = None
        try:
            # Prova a estrarre ASIN dall'URL
            asin = extract_asin_from_url(url)

            # Se non è stato possibile estrarlo dall'URL, cercalo nella pagina
            if not asin:
                asin_element = soup.select_one("input[name='ASIN']")
                if asin_element:
                    asin = asin_element.get("value")
        except Exception:
            asin = "Sconosciuto"

        # Estrai il titolo del prodotto
        title_element = soup.select_one("#productTitle")
        title = title_element.text.strip() if title_element else "Titolo non disponibile"

        # Estrai il prezzo
        price = "Prezzo non disponibile"
        price_elements = [
            soup.select_one("#priceblock_ourprice"),
            soup.select_one("#priceblock_dealprice"),
            soup.select_one(".a-price .a-offscreen"),
            soup.select_one("#price"),
        ]
        for element in price_elements:
            if element and element.text.strip():
                price = element.text.strip()
                break

        # Estrai immagini
        images = []
        # Prova a estrarre dal blocco immagini principale
        img_container = soup.select_one("#imgTagWrapperId img")
        if img_container and img_container.get("data-old-hires"):
            images.append(img_container.get("data-old-hires"))
        elif img_container and img_container.get("src"):
            images.append(img_container.get("src"))

        # Cerca immagini aggiuntive
        img_thumbs = soup.select("#altImages .a-button-thumbnail img")
        for img in img_thumbs:
            if img.get("src"):
                src = img.get("src")
                # Converti URL thumbnail in URL immagine grande
                src = src.replace("._SS40_", "._SL500_")
                if src not in images:
                    images.append(src)

        # Estrai descrizione
        description = ""
        desc_elements = [
            soup.select_one("#productDescription"),
            soup.select_one("#feature-bullets"),
            soup.select_one("#aplus"),
        ]
        for element in desc_elements:
            if element:
                description += element.text.strip() + "\n\n"

        # Estrai specifiche del prodotto
        specifications = {}
        specs_table = soup.select("#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr, .a-keyvalue tr")
        for row in specs_table:
            key_elem = row.select_one("th, .a-span3")
            val_elem = row.select_one("td, .a-span9")
            if key_elem and val_elem:
                key = key_elem.text.strip()
                value = val_elem.text.strip()
                specifications[key] = value

        # Estrai valutazione
        rating_element = soup.select_one("#acrPopover")
        rating = rating_element.get("title") if rating_element else "Valutazione non disponibile"

        # Estrai numero di recensioni
        reviews_element = soup.select_one("#acrCustomerReviewText")
        reviews = reviews_element.text.strip() if reviews_element else "0 recensioni"

        # Estrai disponibilità
        availability = "Disponibilità sconosciuta"
        availability_elements = [
            soup.select_one("#availability"),
            soup.select_one("#deliveryMessageMirId"),
        ]
        for element in availability_elements:
            if element and element.text.strip():
                availability = element.text.strip()
                break

        # Estrai categoria prodotto
        category = ""
        breadcrumbs = soup.select("#wayfinding-breadcrumbs_feature_div li")
        if breadcrumbs:
            categories = []
            for crumb in breadcrumbs:
                if crumb.text.strip() and "›" not in crumb.text:
                    categories.append(crumb.text.strip())
            category = " > ".join(categories)

        # Estrai prodotti correlati/consigliati
        related_products = []
        related_elements = soup.select("#similarity-carousel .a-carousel-card, #anonCarousel1 .a-carousel-card")
        for element in related_elements[:5]:  # Limita a 5 prodotti correlati
            try:
                related_title_elem = element.select_one(".a-size-base")
                related_link_elem = element.select_one("a")

                if related_title_elem and related_link_elem:
                    related_title = related_title_elem.text.strip()
                    related_link = urljoin(self.base_url, related_link_elem.get("href"))

                    related_products.append({
                        "title": related_title,
                        "url": related_link,
                    })
            except Exception:
                continue

        return {
            "asin": asin,
            "url": url,
            "title": title,
            "price": price,
            "description": description,
            "specifications": specifications,
            "images": images,
            "rating": rating,
            "reviews": reviews,
            "availability": availability,
            "category": category,
            "related_products": related_products,
            "timestamp": time.time(),
        }

    def close(self):
        """
        Chiude le risorse del crawler (sessione)
        """
        if hasattr(self.session, 'close'):
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
