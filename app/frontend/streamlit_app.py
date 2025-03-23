import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image

# Aggiungi il path del progetto per l'importazione dei moduli
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.config import settings
from app.utils.helpers import is_valid_amazon_url, format_timestamp

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configura la pagina Streamlit
st.set_page_config(
    page_title=settings.STREAMLIT_TITLE,
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Funzioni di utilità per le API
def get_api_url(endpoint: str) -> str:
    """
    Costruisce l'URL per una API endpoint
    """
    # In locale, l'API è in esecuzione sulla porta 8080
    # In produzione, tutto è sulla stessa porta
    if settings.ENVIRONMENT == "development":
        return f"http://localhost:8080{settings.API_V1_STR}{endpoint}"
    else:
        return f"{settings.API_V1_STR}{endpoint}"


def search_products(query: str, max_products: int = 20, use_cloudscraper: bool = True) -> Dict[str, Any]:
    """
    Chiama l'API di ricerca prodotti
    """
    api_url = get_api_url("/search")

    try:
        response = requests.post(
            api_url,
            json={
                "query": query,
                "max_products": max_products,
                "use_cloudscraper": use_cloudscraper,
            },
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Errore API: {response.status_code} - {response.text}")
            return {"error": response.text, "products": [], "count": 0}

    except Exception as e:
        st.error(f"Errore durante la chiamata API: {e}")
        return {"error": str(e), "products": [], "count": 0}


def get_product_details(url: str, use_cloudscraper: bool = True) -> Dict[str, Any]:
    """
    Chiama l'API per ottenere i dettagli di un prodotto
    """
    api_url = get_api_url("/product/details")

    try:
        response = requests.post(
            api_url,
            json={
                "url": url,
                "use_cloudscraper": use_cloudscraper,
            },
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Errore API: {response.status_code} - {response.text}")
            return {"error": response.text}

    except Exception as e:
        st.error(f"Errore durante la chiamata API: {e}")
        return {"error": str(e)}


# Funzioni per visualizzare i risultati
def display_product_card(product: Dict[str, Any], col):
    """
    Visualizza una card prodotto
    """
    with col:
        st.subheader(product["title"][:50] + "..." if len(product["title"]) > 50 else product["title"])

        if product.get("image_url"):
            # Utilizza st.image invece del componente HTML
            try:
                st.image(product["image_url"], width=150)
            except Exception:
                st.info("Immagine non disponibile")

        st.write(f"**Prezzo:** {product['price']}")

        if product.get("rating"):
            st.write(f"**Valutazione:** {product['rating']} ({product.get('reviews', '0')} recensioni)")

        st.write(f"**ASIN:** {product['asin']}")

        # Link al prodotto
        st.markdown(f"[Vedi su Amazon]({product['url']})")

        # Pulsante per i dettagli
        if st.button("Dettagli", key=f"details_{product['asin']}"):
            st.session_state.selected_product_url = product['url']
            st.experimental_rerun()


def display_product_details(product: Dict[str, Any]):
    """
    Visualizza i dettagli di un prodotto
    """
    # Titolo
    st.title(product["title"])

    # Layout a due colonne
    col1, col2 = st.columns([1, 2])

    with col1:
        # Immagine principale
        if product.get("images") and len(product["images"]) > 0:
            try:
                st.image(product["images"][0], width=300)
            except Exception:
                st.info("Immagine non disponibile")

        # Informazioni di base
        st.subheader("Informazioni di base")
        st.write(f"**Prezzo:** {product['price']}")
        st.write(f"**ASIN:** {product['asin']}")
        st.write(f"**Categoria:** {product.get('category', 'N/A')}")
        st.write(f"**Disponibilità:** {product.get('availability', 'N/A')}")
        st.write(f"**Valutazione:** {product.get('rating', 'N/A')}")
        st.write(f"**Recensioni:** {product.get('reviews', 'N/A')}")

        # Data di estrazione
        st.write(f"**Data estrazione:** {format_timestamp(product['timestamp'])}")

        # Link al prodotto
        st.markdown(f"[Vedi su Amazon]({product['url']})")

    with col2:
        # Descrizione
        st.subheader("Descrizione")
        if product.get("description"):
            st.write(product["description"])
        else:
            st.info("Nessuna descrizione disponibile")

        # Specifiche
        if product.get("specifications") and len(product["specifications"]) > 0:
            st.subheader("Specifiche tecniche")
            for key, value in product["specifications"].items():
                st.write(f"**{key}:** {value}")

    # Galleria immagini
    if product.get("images") and len(product["images"]) > 1:
        st.subheader("Galleria immagini")
        # Crea una griglia di immagini
        image_cols = st.columns(4)  # Massimo 4 immagini per riga
        for i, img_url in enumerate(product["images"][1:]):  # Salta la prima immagine (già mostrata)
            with image_cols[i % 4]:
                try:
                    st.image(img_url, width=150)
                except Exception:
                    st.info("Immagine non disponibile")

    # Prodotti correlati
    if product.get("related_products") and len(product["related_products"]) > 0:
        st.subheader("Prodotti correlati")
        related_cols = st.columns(min(3, len(product["related_products"])))

        for i, related in enumerate(product["related_products"][:3]):  # Mostra massimo 3 prodotti correlati
            with related_cols[i]:
                st.write(related["title"])
                st.markdown(f"[Vedi su Amazon]({related['url']})")


# Interfaccia principale
def main():
    # Titolo dell'app
    st.title("Amazon Crawler")
    st.write("Ricerca e analisi di prodotti Amazon")

    # Barra laterale
    st.sidebar.title("Opzioni")

    # Opzione per usare CloudScraper
    use_cloudscraper = st.sidebar.checkbox("Usa CloudScraper (per bypassare protezioni)", value=True)

    # Separatore
    st.sidebar.divider()

    # Informazioni sull'applicazione
    st.sidebar.info(
        """
        **Amazon Crawler**

        Questo strumento ti permette di cercare prodotti su Amazon
        e visualizzare dettagli e informazioni sui prodotti trovati.

        Utile per monitorare prezzi, confrontare prodotti e tenere
        traccia della disponibilità.
        """
    )

    # Tabs per diverse funzionalità
    tab1, tab2 = st.tabs(["Ricerca Prodotti", "Analisi Prodotto"])

    # Tab 1: Ricerca Prodotti
    with tab1:
        st.header("Ricerca Prodotti")

        # Input di ricerca
        search_query = st.text_input("Inserisci la query di ricerca", key="search_query")
        max_products = st.slider("Numero massimo di prodotti", min_value=5, max_value=50, value=20, step=5)

        # Pulsante di ricerca
        if st.button("Cerca"):
            if search_query:
                with st.spinner("Ricerca in corso..."):
                    # Memorizza i risultati della ricerca nella session state
                    results = search_products(search_query, max_products, use_cloudscraper)
                    st.session_state.search_results = results

                    # Visualizza i risultati
                    if "error" in results:
                        st.error(f"Errore durante la ricerca: {results['error']}")
                    else:
                        st.success(f"Trovati {results['count']} prodotti per '{results['query']}'")

                        # Visualizza i prodotti in una griglia
                        if results['count'] > 0:
                            # Crea una griglia di 3 colonne
                            num_cols = 3
                            rows = (results['count'] + num_cols - 1) // num_cols  # Arrotonda per eccesso

                            for row in range(rows):
                                cols = st.columns(num_cols)
                                for col_idx in range(num_cols):
                                    product_idx = row * num_cols + col_idx
                                    if product_idx < results['count']:
                                        display_product_card(results['products'][product_idx], cols[col_idx])
            else:
                st.warning("Inserisci una query di ricerca")

        # Visualizza i risultati precedenti se presenti
        if "search_results" in st.session_state and not search_query:
            results = st.session_state.search_results
            st.success(f"Ultimi risultati: {results['count']} prodotti per '{results['query']}'")

            # Visualizza i prodotti in una griglia
            if results['count'] > 0:
                # Crea una griglia di 3 colonne
                num_cols = 3
                rows = (results['count'] + num_cols - 1) // num_cols  # Arrotonda per eccesso

                for row in range(rows):
                    cols = st.columns(num_cols)
                    for col_idx in range(num_cols):
                        product_idx = row * num_cols + col_idx
                        if product_idx < results['count']:
                            display_product_card(results['products'][product_idx], cols[col_idx])

    # Tab 2: Analisi Prodotto
    with tab2:
        st.header("Analisi Prodotto")

        # Input URL diretto
        product_url = st.text_input("Inserisci l'URL del prodotto Amazon", key="product_url")

        # Se proviene dalla selezione di un prodotto
        if "selected_product_url" in st.session_state:
            product_url = st.session_state.selected_product_url
            # Aggiorna l'input
            st.experimental_set_query_params(product_url=product_url)

        # Pulsante di analisi
        analyze_button = st.button("Analizza")

        if analyze_button or (product_url and "last_analyzed_url" not in st.session_state):
            if product_url:
                if not is_valid_amazon_url(product_url):
                    st.error("L'URL fornito non sembra essere un URL Amazon valido")
                else:
                    with st.spinner("Analisi in corso..."):
                        # Ottieni i dettagli del prodotto
                        result = get_product_details(product_url, use_cloudscraper)

                        if "error" in result:
                            st.error(f"Errore durante l'analisi: {result['error']}")
                        else:
                            # Memorizza l'ultimo URL analizzato
                            st.session_state.last_analyzed_url = product_url
                            # Memorizza i dettagli del prodotto
                            st.session_state.product_details = result["product"]

                            # Visualizza i dettagli del prodotto
                            display_product_details(result["product"])
            else:
                st.warning("Inserisci l'URL di un prodotto Amazon")

        # Visualizza i dettagli precedenti se presenti
        elif "product_details" in st.session_state:
            display_product_details(st.session_state.product_details)


# Funzione principale
if __name__ == "__main__":
    main()
