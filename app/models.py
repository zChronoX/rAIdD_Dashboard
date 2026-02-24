from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# REQUISITO 3.1: AUTENTICAZIONE 

    #Modello per la gestione degli account degli operatori di sistema.
    #Memorizza le credenziali di accesso utilizzando l'hashing sicuro delle password.
    
class Operatore(db.Model):
    
    __tablename__ = 'operatori'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        #Genera e salva l'hash sicuro della password fornita in chiaro
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        #Verifica se la password in chiaro corrisponde all'hash salvato nel database.
        return check_password_hash(self.password_hash, password)
      
    def __repr__(self):
        #Serve per stampare in modo leggibile l'oggetto Operatore in caso di debug.
        return f"<Operatore {self.username}>"


# REQUISITO 3.3: GESTIONE DISPOSITIVI

    #Modello per la gestione dell'inventario hardware.
    #Traccia lo stato logistico (Disponibile, In Uso, Manutenzione) e lo stato 
    #diagnostico (batteria, ultima sincronizzazione) di ogni tracker Fitbit.
    
class Dispositivo(db.Model):
    __tablename__ = 'dispositivi'
    
    id = db.Column(db.String(50), primary_key=True) 
    modello = db.Column(db.String(50), default="Fitbit Inspire 3")
    stato = db.Column(db.String(20), default="Disponibile") 
    batteria = db.Column(db.String(10))
    ultima_sincronizzazione = db.Column(db.String(100))
    
    # Relazione 1-a-Molti: un dispositivo può avere molte assegnazioni (storico)
    assegnazioni = db.relationship('Assegnazione', backref='dispositivo', lazy=True)

    def __repr__(self):
        return f"<Dispositivo {self.id} - {self.stato}>"


# REQUISITO 3.2: GESTIONE PAZIENTI E DATI LOGISTICI

    #Modello per la gestione anagrafica e logistica del paziente.
    #Contiene le coordinate geografiche e i riferimenti temporali necessari
    #per l'analisi spaziale dei dispositivi assegnati.
    
class Paziente(db.Model):
    __tablename__ = 'pazienti'
    
    id = db.Column(db.String(50), primary_key=True)
    regione = db.Column(db.String(100))
    provincia = db.Column(db.String(100))
    latitudine = db.Column(db.Float)
    longitudine = db.Column(db.Float)
    nazione = db.Column(db.String(50))
    fuso_orario = db.Column(db.String(50))
    data_attivazione = db.Column(db.String(50)) 
    # Eliminando un paziente, si elimina anche il suo storico assegnazioni e i suoi dati biometrici
    assegnazioni = db.relationship('Assegnazione', backref='paziente', lazy=True, cascade="all, delete-orphan")
    dati_biometrici = db.relationship('DatoBiometricoGiornaliero', backref='paziente', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Paziente {self.id}>"


# DATI BIOMETRICI

    #Modello per l'archiviazione dei riepiloghi clinici giornalieri.
    #Aggrega i dati estratti dai log JSON/CSV per fornire una base dati leggera
    #e ottimizzata per la renderizzazione dei grafici nel frontend.
    
class DatoBiometricoGiornaliero(db.Model):
    __tablename__ = 'dati_biometrici'
    
    id = db.Column(db.Integer, primary_key=True)
    # Foreign Key che collega il dato al paziente specifico
    paziente_id = db.Column(db.String(50), db.ForeignKey('pazienti.id'), nullable=False)
    data_registrazione = db.Column(db.String(10), nullable=False) # Formato YYYY-MM-DD
    
    # Parametri clinici medi giornalieri aggregati
    frequenza_cardiaca_media = db.Column(db.Float, nullable=True)
    spo2_media = db.Column(db.Float, nullable=True)
    passi_totali = db.Column(db.Integer, nullable=True)
    minuti_attivita = db.Column(db.Integer, nullable=True)
    minuti_sonno = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<Biometria Paziente {self.paziente_id} - Data {self.data_registrazione}>"


# REQUISITO 3.4/3.5: WORKFLOW ASSEGNAZIONI/RESTITUZIONI DISPOSITIVI

    #La tabella delle assegnazioni non si limita a collegare Paziente e Dispositivo, ma storicizza le transazioni
    #registrando data di consegna e data di restituzione.
    #Se data_restituzione è NULL, significa che il dispositivo è attualmente al polso del paziente.
    
class Assegnazione(db.Model):
    __tablename__ = 'assegnazioni'
    
    id = db.Column(db.Integer, primary_key=True)
    paziente_id = db.Column(db.String(50), db.ForeignKey('pazienti.id'), nullable=False)
    dispositivo_id = db.Column(db.String(50), db.ForeignKey('dispositivi.id'), nullable=False)
    
    # Timestamp logistici
    data_assegnazione = db.Column(db.DateTime, default=datetime.utcnow)
    data_restituzione = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        stato = "Attiva" if self.data_restituzione is None else "Conclusa"
        return f"<Assegnazione {self.id} | Paz:{self.paziente_id} Disp:{self.dispositivo_id} [{stato}]>"