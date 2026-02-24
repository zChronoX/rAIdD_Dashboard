# Usa un'immagine Python ufficiale, ottimizzata e leggera (slim)
FROM python:3.9-slim

# Imposta la cartella di lavoro principale all'interno del container
WORKDIR /app

# Aggiorna il sistema e installa le librerie C necessarie per compilare psycopg2 (driver PostgreSQL)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia il file delle dipendenze per sfruttare la cache dei layer di Docker
COPY requirements.txt .

# Installa i pacchetti Python senza salvare la cache per mantenere l'immagine leggera
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice sorgente nell'ambiente virtuale
COPY . .

# Indica la porta di esposizione del container (utile a livello documentativo)
EXPOSE 5000

# Comando di avvio del server in modalita' sviluppo
CMD ["python", "run.py"]