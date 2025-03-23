#!/bin/bash

# Script di entrypoint per avviare sia FastAPI che Streamlit nello stesso container

# Installa il pacchetto procps per il comando ps se non è presente
if ! command -v ps &> /dev/null; then
    echo "Installazione di procps per il comando ps..."
    apt-get update && apt-get install -y procps
fi

# Avvia FastAPI in background
python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 &

# Memorizza il PID di FastAPI per il controllo successivo
FASTAPI_PID=$!

# Attendi che FastAPI sia avviato
echo "Attesa avvio FastAPI..."
sleep 3

# Controlla se FastAPI è in esecuzione
if ps -p $FASTAPI_PID > /dev/null 2>&1; then
    echo "FastAPI avviato correttamente (PID: $FASTAPI_PID)"
else
    echo "Errore nell'avvio di FastAPI"
    exit 1
fi

# Avvia Streamlit sul porto 8502 all'interno del container
# Google Cloud Run esporrà il porto $PORT (8080) come proxy
# Streamlit sarà accessibile tramite l'endpoint /streamlit
echo "Avvio Streamlit..."
streamlit run app/frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.baseUrlPath /streamlit

# Se Streamlit termina, termina anche FastAPI
kill $FASTAPI_PID 2>/dev/null