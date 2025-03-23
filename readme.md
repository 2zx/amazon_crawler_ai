# Amazon Crawler

Un'applicazione per il crawling di prodotti Amazon basata su Docker, FastAPI e Streamlit.

## Funzionalità

- 🔍 Ricerca di prodotti su Amazon
- 📊 Visualizzazione dei dettagli dei prodotti
- 🕸️ Crawling con Selenium o requests
- 🌐 Dashboard Streamlit per l'interfaccia utente
- 🚀 API RESTful per l'integrazione con altri sistemi
- 🐳 Containerizzazione con Docker
- ☁️ Deployment su Google Cloud Run

## Tecnologie utilizzate

- **Backend**: FastAPI, Python 3.11
- **Frontend**: Streamlit
- **Crawling**: BeautifulSoup, Requests, CloudScraper
- **Containerizzazione**: Docker
- **Deployment**: Google Cloud Run

## Requisiti

- Python 3.11+
- Docker e Docker Compose
- Chrome (per Selenium)

## Struttura del progetto

```
amazon-crawler/
├── app/
│   ├── api/              # Endpoint API FastAPI
│   ├── core/             # Configurazione e logging
│   ├── crawlers/         # Crawler per Amazon
│   ├── db/               # Modelli e sessione del database
│   ├── frontend/         # Applicazione Streamlit
│   └── utils/            # Funzioni di utilità
├── tests/                # Test unitari e di integrazione
├── Dockerfile            # Configurazione Docker
├── docker-compose.yml    # Configurazione Docker Compose
├── requirements.txt      # Dipendenze Python
└── cloudbuild.yaml       # Configurazione Google Cloud Build
```

## Come iniziare

### Installazione locale

1. Clona il repository
   ```bash
   git clone https://github.com/yourusername/amazon-crawler.git
   cd amazon-crawler
   ```

2. Crea e attiva un ambiente virtuale
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # oppure
   venv\Scripts\activate     # Windows
   ```

3. Installa le dipendenze
   ```bash
   pip install -r requirements.txt
   ```

4. Crea un file `.env` con le variabili d'ambiente necessarie
   ```
   ENVIRONMENT=development
   DEBUG=true
   ```

5. Avvia l'applicazione
   ```bash
   uvicorn app.main:app --reload
   ```

6. In un altro terminale, avvia Streamlit
   ```bash
   streamlit run app/frontend/streamlit_app.py
   ```

### Utilizzo con Docker

1. Costruisci e avvia i container
   ```bash
   docker-compose up --build
   ```

2. Accedi all'applicazione
   - API: http://localhost:8080
   - Streamlit: http://localhost:8501

## Deployment su Google Cloud Run

### Prerequisiti

- Account Google Cloud con fatturazione abilitata
- Google Cloud SDK installato e configurato
- Un progetto Google Cloud attivo

### Passi per il deployment

1. Abilita le API necessarie
   ```bash
   gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
   ```

2. Crea un trigger di build
   ```bash
   gcloud builds triggers create github \
     --repo=YOUR_GITHUB_REPO \
     --branch-pattern="main" \
     --build-config="cloudbuild.yaml"
   ```

3. Esegui manualmente un build e deploy
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

4. Ottieni l'URL del servizio
   ```bash
   gcloud run services describe amazon-crawler --platform managed --region europe-west1 --format="value(status.url)"
   ```

## Note sull'utilizzo

- **Rate limiting**: Per evitare di essere bloccati da Amazon, è importante impostare un ritardo tra le richieste.
- **User-Agent**: L'applicazione utilizza la rotazione degli User-Agent per sembrare più umana.
- **Selenium**: Per i casi più complessi, è possibile utilizzare Selenium per il crawling.

## Licenza

MIT License