![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/javascript-%23F7DF1E.svg?style=for-the-badge&logo=javascript&logoColor=black)
![Bootstrap](https://img.shields.io/badge/bootstrap-%238511FA.svg?style=for-the-badge&logo=bootstrap&logoColor=white)

![Leaflet](https://img.shields.io/badge/Leaflet-199903?style=for-the-badge&logo=Leaflet&logoColor=white)
![Jinja2](https://img.shields.io/badge/jinja-%23b41717.svg?style=for-the-badge&logo=jinja&logoColor=white)

# rAIdD - Piattaforma di Monitoraggio Dispositivi Wearable

Questa è l'applicazione web per la gestione logistica e l'analisi della telemetria dei dispositivi wearable (Fitbit Inspire 3) del progetto rAIdD. 
Il sistema è interamente containerizzato: questo significa che **non è necessario installare Python, PostgreSQL o configurare database locali** per testare il progetto. L'infrastruttura viene orchestrata automaticamente da Docker.

---

## Guida all'Avvio Rapido (Build & Deploy)

### Prerequisiti
Per far partire il progetto sul tuo computer, hai bisogno solo di uno strumento:
* **Docker Desktop:** Il motore che farà girare l'applicazione in un ambiente virtuale isolato. (Scaricabile da docker.com)

**Attenzione:** Dopo aver installato Docker Desktop, assicurati di avviarlo (devi vedere l'icona della balena nella barra delle applicazioni o la scritta "Engine Running" nel programma) prima di procedere con i passaggi successivi.

### Passo 1: Scarica il codice sorgente

**Download diretto**
1. Vai sulla pagina GitHub del progetto.
2. Clicca sul pulsante verde **Code** in alto a destra e seleziona **Download ZIP**.
3. Estrai la cartella ZIP appena scaricata sul tuo computer.
4. Entra nella cartella estratta, fai clic destro in uno spazio vuoto e seleziona **Apri nel Terminale** (su Windows 11) oppure apri il tuo prompt dei comandi e naviga fino a quella cartella usando il comando `cd`.

### Passo 2. Avvio di Docker

1.  Aprire il terminale nella cartella.
2.  Eseguire il comando per costruire e avviare i container:

    ```bash
    docker-compose up --build
    ```

3.  Attendere che i log confermino l'avvio dei servizi:
    * `db-1`: Database avviato sulla porta 5432.
    * `web-1`: Container web avviato sulla porta 5000.


### Passo 3. Accesso all'Applicazione
Una volta che Docker ha terminato l'avvio, puoi accedere all'interfaccia web tramite il tuo browser:

1.  Apri il browser (Chrome, Firefox, Edge, ecc.).
2.  Vai all'indirizzo: **http://localhost:5000**
3.  Effettua il login usando le credenziali di default:
    * **Username:** `admin`
    * **Password:** `admin123`

---

## Test della Funzionalità di Upload

Per testare correttamente il motore di importazione e la visualizzazione dei grafici clinici, è necessario disporre di un archivio **ZIP** ottenuto tramite **Google Takeout**. 

Poiché il sistema ha natura prototipale e non prevede l'integrazione diretta con le API proprietarie di Fitbit, il caricamento dei dati si basa sulla procedura di **estrazione manuale** e condivisione tramite cloud descritta nei requisiti operativi del progetto.

### Istruzioni per il test:
1. **Ottenimento dati:** Seguire la procedura di esportazione dati Google Takeout per l'account associato al dispositivo Fitbit Inspire 3.
2. **Caricamento:** Utilizzare il file ZIP generato nella sezione "Upload Dati" della dashboard.
3. **Elaborazione:** Il sistema analizzerà i file JSON contenuti nell'archivio (es. frequenza cardiaca, passi, sonno) per calcolare le medie giornaliere e popolare automaticamente la dashboard statistica e il profilo clinico del paziente.

> **Nota:** Il caricamento di uno ZIP non conforme agli standard di Google Takeout o privo dei file di telemetria necessari potrebbe causare errori di validazione durante il parsing.

---

## Struttura del Repository

L'organizzazione dei file segue gli standard delle applicazioni web Python/Flask containerizzate, con una netta separazione tra logica di backend, asset statici e template HTML:

### Root del Progetto
* `/app`: Directory che contiene il codice sorgente dell'applicazione.
* `docker-compose.yml`: File di orchestrazione per la gestione dei container Docker (Web App + Database PostgreSQL).
* `Dockerfile`: Istruzioni per la creazione dell'immagine Docker del backend Python.
* `requirements.txt`: Elenco delle dipendenze Python necessarie (Flask, SQLAlchemy, ecc.).
* `config.py`: Gestione delle variabili di configurazione e connessione al database.
* `run.py`: Script per l'avvio dell'applicazione.

### /app (Backend)
Contiene il cuore pulsante dell'applicativo, gestito tramite il pattern MVC:
* `routes.py`: Definizione di tutti gli endpoint (Controller) e gestione della logica di navigazione.
* `models.py`: Definizione delle classi del database (Entità) e delle relazioni E-R tramite SQLAlchemy.
* `utils.py`: Motore di elaborazione dati per il parsing e l'estrazione della telemetria dagli archivi ZIP dei wearable.
* `__init__.py`: Inizializza l'applicazione Flask e configura il database.
* `/static`: Contiene le risorse statiche che vengono inviate al browser del client.
* `/templates`: Contiene i file HTML strutturati per il motore di templating Jinja2.

### /static (Frontend)
Contiene le risorse statiche che vengono inviate al browser del client:
* **/css**: 
    * `style.css`: Foglio di stile personalizzato per il layout e la formattazione dei componenti UI.
* **/js**: 
    * `dashboard.js`: Logica per l'inizializzazione della mappa Leaflet e dei grafici statistici.
    * `dispositivi.js`: File JavaScript per la gestione dei dispositivi.
    * `profilo.js`: File JavaScript per la gestione del profilo.

### /templates (View Layer)
Contiene i file HTML strutturati per il motore di templating **Jinja2**:
* `dashboard.html`: Dashboard principale con la mappa e i KPI globali.
* `login.html`: Pagina di login.
* `pazienti.html`: Lista anagrafica e gestione CRUD dei pazienti.
* `dispositivi.html`: Inventario hardware e stato dei wearable.
* `assegnazioni.html`: Interfaccia per la gestione dei flussi logistici di consegna e restituzione.
* `profilo.html`: Scheda clinica dettagliata con grafici biometrici e statistiche di monitoraggio.
* `upload.html`: Form per il caricamento degli archivi ZIP e visualizzazione dei risultati di importazione.
* `upload_results.html`: Risultati dell'upload.
* `storico_dispositivo.html`: Storico delle assegnazioni di un dispositivo.

---

## Sicurezza e Privacy

Il sistema è stato progettato seguendo il principio della **Privacy by Design**, adottando misure tecniche volte a garantire la protezione dei dati e la sicurezza degli accessi, pur mantenendo la natura prototipale dell'elaborato.

### 1. Pseudonimizzazione dei Dati
In conformità con i requisiti di progetto, la piattaforma non tratta dati personali identificativi in chiaro:
* **Identificativi Univoci:** Ogni paziente è censito esclusivamente tramite un ID pseudonimo.
* **Disaccoppiamento:** Non esiste nel database alcun collegamento diretto tra gli identificativi tecnici e le identità reali dei pazienti (nomi, cognomi o codici fiscali).

### 2. Gestione Sicura delle Credenziali
L'accesso alla dashboard è protetto da un sistema di autenticazione per operatori:
* **Hashing Crittografico:** Le password non vengono mai salvate in chiaro. Viene utilizzata la libreria `Werkzeug.security` per generare hash robusti tramite algoritmi di derivazione delle chiavi (PBKDF2 con salt casuale).
* **Controllo Accessi:** Tutte le rotte sensibili del backend sono protette da decoratori di sessione, impedendo l'accesso non autorizzato ai dati tramite manipolazione degli URL.

### 3. Minimizzazione e Trattamento dei Dati Biometrici
Per rispettare il divieto di memorizzazione di dati clinici sensibili granulari, il sistema adotta una strategia di **aggregazione al volo**:
* **Elaborazione in Memoria:** Durante l'upload dei file ZIP (Fitbit), i log medici grezzi vengono letti e processati temporaneamente nella memoria volatile del server.
* **Aggregazione Statistica:** Vengono salvate nel database PostgreSQL solo le medie giornaliere e i totali aggregati (BPM medio, SpO2 media, Passi totali, Minuti di sonno).
* **Eliminazione Automatica:** Una volta concluso il calcolo delle metriche necessarie alla visualizzazione dei grafici, i file log originali e i dati granulari vengono immediatamente scartati e non persistono sul server.


---

##  Autore

* Giovanni Maria Contarino, Matricola 1000007029
