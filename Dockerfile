FROM python:3.11-slim

WORKDIR /app

# Installa le dipendenze necessarie
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copia i file dei requisiti
COPY requirements.txt .

# Installa le dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY . .

# Variabili d'ambiente predefinite
ENV PORT=8080
ENV PYTHONPATH=/app

# Espone sia la porta per l'API che per Streamlit
EXPOSE 8080
EXPOSE 8501

# Script di entrypoint che avvia sia FastAPI che Streamlit
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Avvia l'applicazione
CMD ["/entrypoint.sh"]