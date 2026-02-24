import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Inizializzazione globale dell'oggetto SQLAlchemy
db = SQLAlchemy()

#Application Factory: istanzia e configura l'applicazione Flask.
#Questo pattern permette di creare istanze multiple dell'app per i test
#e previene importazioni circolari.
def create_app():

    app = Flask(__name__)
    
    # Importiamo le configurazioni direttamente dal file config.py
    # Questo rende il codice piu' pulito e centralizzato.
    app.config.from_object('config.Config')

    # Colleghiamo il database all'istanza dell'applicazione
    db.init_app(app)

    # Creazione del contesto applicativo per operazioni sul database al momento dell'avvio
    with app.app_context():
        # Importiamo i modelli per permettere a SQLAlchemy di riconoscerli
        from . import models
        
        # Crea tutte le tabelle nel database se non esistono gia'
        db.create_all()
        
        from .models import Operatore
        
        # Controlla se esiste gia' un utente 'admin', altrimenti lo crea.
        # Questo assicura che il sistema non sia mai bloccato al primo avvio.
        if not Operatore.query.filter_by(username='admin').first():
            admin = Operatore(username='admin')
            admin.set_password('admin123') # La password viene automaticamente hashata
            db.session.add(admin)
            db.session.commit()
            print("Sistema: Utente di default 'admin' creato con successo.")

    # Registrazione dei Blueprint (le rotte dell'applicazione definite in routes.py)
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app