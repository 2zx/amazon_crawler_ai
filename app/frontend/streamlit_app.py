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


def get_watchlist() -> List[Dict[str, Any]]:
    """
    Chiama l'API per ottenere la watch list
    """
    api_url = get_api_url("/watchlist")

    try:
        response = requests.get(
            api_url,
            timeout=10,
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Errore API: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        st.error(f"Errore durante la chiamata API: {e}")
        return []


def add_to_watchlist(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chiama l'API per aggiungere un prodotto alla watch list
    """
    api_url = get_api_url("/watchlist/add")

    try:
        response = requests.post(
            api_url,
            json=data,
            timeout=30,  # Timeout più lungo perché potrebbe richiedere un crawling
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Errore API: {response.status_code} - {response.text}")
            return {"error": response.text}

    except Exception as e:
        st.error(f"Errore durante la chiamata API: {e}")
        return {"error": str(e)}


def remove_from_watchlist(job_id: int) -> bool:
    """
    Chiama l'API per rimuovere un prodotto dalla watch list
    """
    api_url = get_api_url(f"/watchlist/{job_id}")

    try:
        response = requests.delete(
            api_url,
            timeout=10,
        )

        if response.status_code == 200:
            return True
        else:
            st.error(f"Errore API: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        st.error(f"Errore durante la chiamata API: {e}")
        return False


def update_watchlist_item(job_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chiama l'API per aggiornare un prodotto nella watch list
    """
    api_url = get_api_url(f"/watchlist/{job_id}")

    try:
        response = requests.put(
            api_url,
            json=data,
            timeout=10,
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

        # Pulsante per aggiungere alla watch list
        if st.button("Aggiungi alla Watch List", key=f"watchlist_{product['asin']}"):
            add_product_to_watchlist(product)


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


def display_watchlist_item(item: Dict[str, Any], col, show_actions=True):
    """
    Visualizza un elemento della watch list
    """
    with col:
        st.subheader(item.get("name") or item["product"]["title"][:50] + "..." if len(item["product"]["title"]) > 50 else item["product"]["title"])

        if item["product"].get("image_url"):
            try:
                st.image(item["product"]["image_url"], width=150)
            except Exception:
                st.info("Immagine non disponibile")

        st.write(f"**Prezzo attuale:** {item['product']['price']}")

        if item.get("target_price"):
            st.write(f"**Prezzo target:** {item['target_price']}")

        # Notifiche attive
        notifications = []
        if item.get("notify_on_price_drop"):
            notifications.append("Calo di prezzo")
        if item.get("notify_on_availability"):
            notifications.append("Disponibilità")

        if notifications:
            st.write(f"**Notifiche:** {', '.join(notifications)}")

        # Stato
        st.write(f"**Stato:** {'Attivo' if item.get('is_active') else 'Inattivo'}")

        # Link al prodotto
        st.markdown(f"[Vedi su Amazon]({item['product']['url']})")

        # Pulsante per visualizzare lo storico prezzi
        if st.button("Storico prezzi", key=f"history_{item['id']}"):
            display_price_history_chart(item['product']['id'])

        # Azioni
        if show_actions:
            col1, col2 = st.columns(2)

            with col1:
                if st.button("Modifica", key=f"edit_{item['id']}"):
                    st.session_state.edit_watchlist_item = item
                    st.experimental_rerun()

            with col2:
                if st.button("Rimuovi", key=f"remove_{item['id']}"):
                    if remove_from_watchlist(item['id']):
                        st.success("Prodotto rimosso dalla Watch List")
                        # Aggiorna la watch list in sessione
                        if "watchlist" in st.session_state:
                            st.session_state.watchlist = [i for i in st.session_state.watchlist if i['id'] != item['id']]
                        st.experimental_rerun()


def display_watchlist_tab():
    """
    Visualizza il tab della Watch List
    """
    st.header("Watch List")

    # Aggiornamento manuale dei prezzi
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Aggiorna prezzi", help="Avvia un aggiornamento manuale dei prezzi"):
            with st.spinner("Aggiornamento prezzi in corso..."):
                try:
                    response = requests.post(
                        get_api_url("/watchlist/update-prices"),
                        params={"limit": 10},
                        timeout=60,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"Aggiornamento completato! "
                                   f"Aggiornati: {result['products_updated']}, "
                                   f"Falliti: {result['products_failed']}, "
                                   f"Notifiche: {result['notifications_sent']}")

                        # Aggiorna la watch list
                        st.session_state.watchlist = get_watchlist()
                        st.experimental_rerun()
                    else:
                        st.error(f"Errore durante l'aggiornamento: {response.text}")
                except Exception as e:
                    st.error(f"Errore: {e}")

    # Form per aggiungere un prodotto manualmente
    with st.expander("Aggiungi prodotto manualmente", expanded=False):
        with st.form("add_product_form"):
            url = st.text_input("URL del prodotto Amazon")
            name = st.text_input("Nome personalizzato (opzionale)")
            target_price = st.number_input("Prezzo target (opzionale)", min_value=0.0, step=0.01, value=0.0)
            col1, col2 = st.columns(2)
            with col1:
                notify_price = st.checkbox("Notifica calo di prezzo", value=True)
            with col2:
                notify_avail = st.checkbox("Notifica disponibilità", value=False)
            email = st.text_input("Email per notifiche (opzionale)")

            submitted = st.form_submit_button("Aggiungi alla Watch List")

            if submitted:
                # Prepara il prodotto
                product = {
                    "url": url,
                    "asin": None  # L'API cercherà di estrarlo dall'URL
                }
                result = add_product_to_watchlist(
                    product,
                    notify_on_price_drop=notify_price,
                    notify_on_availability=notify_avail,
                    target_price=target_price if target_price > 0 else None,
                    name=name if name else None,
                    notification_email=email if email else None
                )
                if result:
                    st.experimental_rerun()

    # Form per modificare un elemento
    if "edit_watchlist_item" in st.session_state:
        item = st.session_state.edit_watchlist_item
        st.subheader(f"Modifica '{item.get('name') or item['product']['title'][:30]}...'")

        with st.form("edit_product_form"):
            name = st.text_input("Nome personalizzato", value=item.get("name") or "")
            target_price = st.number_input(
                "Prezzo target",
                min_value=0.0,
                step=0.01,
                value=float(item.get("target_price") or 0.0)
            )
            col1, col2 = st.columns(2)
            with col1:
                notify_price = st.checkbox(
                    "Notifica calo di prezzo",
                    value=item.get("notify_on_price_drop", True)
                )
            with col2:
                notify_avail = st.checkbox(
                    "Notifica disponibilità",
                    value=item.get("notify_on_availability", False)
                )
            is_active = st.checkbox("Attivo", value=item.get("is_active", True))
            email = st.text_input(
                "Email per notifiche",
                value=item.get("notification_email") or ""
            )

            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Salva modifiche")
            with col2:
                cancel = st.form_submit_button("Annulla")

            if submitted:
                # Prepara i dati
                data = {
                    "name": name if name else None,
                    "notify_on_price_drop": notify_price,
                    "notify_on_availability": notify_avail,
                    "is_active": is_active,
                    "notification_email": email if email else None
                }

                if target_price > 0:
                    data["target_price"] = target_price

                # Chiamata API
                with st.spinner("Aggiorno il prodotto..."):
                    result = update_watchlist_item(item["id"], data)

                    if "error" not in result:
                        st.success("Prodotto aggiornato")
                        # Aggiorna la watch list in sessione
                        if "watchlist" in st.session_state:
                            for i, wl_item in enumerate(st.session_state.watchlist):
                                if wl_item["id"] == item["id"]:
                                    st.session_state.watchlist[i] = result
                                    break
                        # Rimuovi l'elemento in modifica
                        del st.session_state.edit_watchlist_item
                        st.experimental_rerun()

            if cancel:
                del st.session_state.edit_watchlist_item
                st.experimental_rerun()

    # Carica o aggiorna la watch list
    if "watchlist" not in st.session_state or st.button("Aggiorna Watch List"):
        with st.spinner("Caricamento Watch List..."):
            st.session_state.watchlist = get_watchlist()

    # Visualizza la watch list
    if "watchlist" in st.session_state:
        if not st.session_state.watchlist:
            st.info("Non hai ancora prodotti nella Watch List. Aggiungi un prodotto dalla ricerca o inserisci manualmente l'URL.")
        else:
            st.write(f"Prodotti monitorati: {len(st.session_state.watchlist)}")

            # Crea una griglia di 3 colonne
            num_cols = 3
            rows = (len(st.session_state.watchlist) + num_cols - 1) // num_cols  # Arrotonda per eccesso

            for row in range(rows):
                cols = st.columns(num_cols)
                for col_idx in range(num_cols):
                    item_idx = row * num_cols + col_idx
                    if item_idx < len(st.session_state.watchlist):
                        display_watchlist_item(st.session_state.watchlist[item_idx], cols[col_idx])


def get_price_history(product_id: int) -> List[Dict[str, Any]]:
    """
    Chiama l'API per ottenere lo storico dei prezzi di un prodotto
    """
    api_url = get_api_url(f"/product/{product_id}/price-history")

    try:
        response = requests.get(
            api_url,
            timeout=10,
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Errore API: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        st.error(f"Errore durante la chiamata API: {e}")
        return []


def display_price_history_chart(product_id: int):
    """
    Visualizza un grafico dello storico dei prezzi
    """
    # In un'implementazione reale, qui chiameresti l'API
    # Per ora, usiamo dati di esempio

    # Questi dati andrebbero sostituiti con quelli reali dall'API
    price_history = [
        {"date": "2025-03-01", "price": 29.99},
        {"date": "2025-03-08", "price": 27.50},
        {"date": "2025-03-15", "price": 24.99},
        {"date": "2025-03-22", "price": 24.99},
        {"date": "2025-03-24", "price": 19.99},
    ]

    # Crea un DataFrame con lo storico dei prezzi
    if price_history:
        df = pd.DataFrame(price_history)
        df["date"] = pd.to_datetime(df["date"])

        # Crea il grafico
        st.subheader("Storico dei prezzi")
        st.line_chart(df.set_index("date")["price"])
    else:
        st.info("Nessuno storico prezzi disponibile per questo prodotto")


def add_product_to_watchlist(product, notify_on_price_drop=True, notify_on_availability=False,
                             target_price=None, name=None, notification_email=None):
    """
    Funzione centralizzata per aggiungere un prodotto alla watchlist

    Args:
        product: Dizionario con i dati del prodotto (deve contenere almeno 'asin' e 'url')
        notify_on_price_drop: Se inviare notifiche per cali di prezzo
        notify_on_availability: Se inviare notifiche per disponibilità
        target_price: Prezzo target opzionale
        name: Nome personalizzato opzionale
        notification_email: Email per le notifiche opzionale

    Returns:
        Dizionario con il risultato dell'operazione, o None se fallita
    """
    # Prepara i dati
    data = {
        "asin": product.get('asin'),
        "url": product.get('url'),
        "notify_on_price_drop": notify_on_price_drop,
        "notify_on_availability": notify_on_availability
    }

    # Aggiungi i campi opzionali se presenti
    if name:
        data["name"] = name
    if target_price and target_price > 0:
        data["target_price"] = target_price
    if notification_email:
        data["notification_email"] = notification_email

    # Chiamata API
    with st.spinner("Aggiungo il prodotto alla Watch List..."):
        result = add_to_watchlist(data)

        if "error" not in result:
            st.success("Prodotto aggiunto alla Watch List")
            # Aggiorna la watch list in sessione
            if "watchlist" in st.session_state:
                st.session_state.watchlist.insert(0, result)
            return result

    return None


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
    tab1, tab2, tab3 = st.tabs(["Ricerca Prodotti", "Analisi Prodotto", "Watch List"])

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

    # Tab 3: Watch List
    with tab3:
        display_watchlist_tab()


# Funzione principale
if __name__ == "__main__":
    main()
