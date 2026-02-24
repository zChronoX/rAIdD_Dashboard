import os

#Classe di configurazione principale dell'applicazione.
#Gestisce le variabili d'ambiente (sicurezza, database) permettendo 
#una transizione fluida tra l'ambiente di sviluppo locale e la produzione (Docker).
class Config:

    
    # Chiave crittografica per firmare i cookie di sessione.
    # Se non definita nell'ambiente, utilizza un fallback di default.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chiave_segreta_default'
    
    # Stringa di connessione al database PostgreSQL.
    # La priorita' assoluta va alla variabile d'ambiente (fornita dal docker-compose).
    # In caso di esecuzione locale fuori da Docker, usa localhost.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@localhost/raidd_db'
    
    # Disabilita il tracciamento delle modifiche di SQLAlchemy 
    # per risparmiare risorse e memoria sul server.
    SQLALCHEMY_TRACK_MODIFICATIONS = False