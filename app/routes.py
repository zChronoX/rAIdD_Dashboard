import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from datetime import datetime
from sqlalchemy import func

# Importazione dei modelli dati e delle utility
from .models import db, Operatore, Paziente, Dispositivo, Assegnazione, DatoBiometricoGiornaliero
from .utils import processa_file_zip

main_bp = Blueprint('main', __name__)


#SICUREZZA E AUTENTICAZIONE

#Decoratore di sicurezza per proteggere le rotte sensibili.
#Verifica la presenza di 'operatore_id' nella sessione attiva.
#Se assente, reindirizza l'utente alla pagina di login.
    
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'operatore_id' not in session:
            flash("Devi effettuare l'accesso per visualizzare questa pagina.", "warning")
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function


#Gestisce l'accesso degli operatori al sistema gestionale.
#Verifica l'hash della password e inizializza la sessione.
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        operatore = Operatore.query.filter_by(username=username).first()
        
        # Validazione delle credenziali tramite il modello
        if operatore and operatore.check_password(password):
            session['operatore_id'] = operatore.id
            session['username'] = operatore.username
            return redirect(url_for('main.home'))
        else:
            flash('Credenziali non valide, riprova.', 'danger')
            
    return render_template('login.html')

#Distrugge la sessione corrente e disconnette l'operatore.
@main_bp.route('/logout')
def logout():
    session.pop('operatore_id', None)
    session.pop('username', None)
    return redirect(url_for('main.login'))



#DASHBOARD E STATISTICHE


#Controller della pagina principale (Dashboard).
#Calcola in tempo reale i contatori globali interrogando il database
#per fornire un quadro riassuntivo su pazienti e dispositivi.
@main_bp.route('/')
@login_required
def home():
   
    # Contatori globali grezzi
    totale_paz = Paziente.query.count()
    totale_disp = Dispositivo.query.count()
    
    # Calcolo stato logistico dei dispositivi
    assegnati = Assegnazione.query.filter_by(data_restituzione=None).count()
    tutti_disponibili = Dispositivo.query.filter_by(stato='Disponibile').all()
    # Un dispositivo è considerato realmente disponibile se la batteria non è a 0
    disponibili = sum(1 for d in tutti_disponibili if d.batteria is None or int(d.batteria) > 0)
    
    # Calcolo stato logistico dei pazienti (Attivi / Restituiti / Da Assegnare)
    pazienti = Paziente.query.all()
    paz_attivi, paz_restituiti, paz_da_assegnare = 0, 0, 0

    for p in pazienti:
        ass_attiva = Assegnazione.query.filter_by(paziente_id=p.id, data_restituzione=None).first()
        storico = Assegnazione.query.filter_by(paziente_id=p.id).count()
        if ass_attiva:
            paz_attivi += 1
        elif storico > 0:
            paz_restituiti += 1
        else:
            paz_da_assegnare += 1
            
    return render_template('dashboard.html',
                           totale_pazienti=totale_paz,
                           pazienti_attivi=paz_attivi,
                           pazienti_restituiti=paz_restituiti,
                           pazienti_da_assegnare=paz_da_assegnare,
                           totale_dispositivi=totale_disp,
                           assegnati=assegnati,
                           disponibili=disponibili,
                           username=session.get('username'))



#Endpoint API RESTful. Fornisce i dati in formato JSON per popolare
#la mappa geografica interattiva e i grafici Chart.js della dashboard.
@main_bp.route('/api/dashboard_data')
@login_required
def api_dashboard_data():
    
    
    pazienti = Paziente.query.all()
    dati_pazienti = []
    paz_attivi, paz_restituiti, paz_da_assegnare = 0, 0, 0
    
    for p in pazienti:
        #Popolamento coordinate e stato per i marker della mappa
        if p.latitudine and p.longitudine:
            assegnazione_attiva = Assegnazione.query.filter_by(paziente_id=p.id, data_restituzione=None).first()
            ha_disp = False
            disp_id = "Nessuno"
            data_ass = "N/D"
            
            if assegnazione_attiva:
                ha_disp = True
                disp_id = assegnazione_attiva.dispositivo_id
                if assegnazione_attiva.data_assegnazione:
                    data_ass = assegnazione_attiva.data_assegnazione.strftime("%d/%m/%Y")
                    
            dati_pazienti.append({
                "id": p.id,
                "lat": p.latitudine, "lng": p.longitudine,
                "ha_dispositivo": ha_disp,
                "dispositivo_id": disp_id,
                "data_assegnazione": data_ass
            })

        #Calcolo dei contatori per il grafico a ciambella
        assegnazione_attiva = Assegnazione.query.filter_by(paziente_id=p.id, data_restituzione=None).first()
        storico = Assegnazione.query.filter_by(paziente_id=p.id).count()
        if assegnazione_attiva:
            paz_attivi += 1
        elif storico > 0:
            paz_restituiti += 1
        else:
            paz_da_assegnare += 1
            
    #Aggregazione SQL per il grafico a barre regionale
    statistiche_regioni = db.session.query(Paziente.regione, func.count(Paziente.id)).group_by(Paziente.regione).all()
    regioni_nomi = [r[0] for r in statistiche_regioni if r[0]]
    regioni_valori = [r[1] for r in statistiche_regioni if r[0]]
    
    return jsonify({
        "pazienti": dati_pazienti,
        "regioni_nomi": regioni_nomi,
        "regioni_valori": regioni_valori,
        "stati_pazienti": [paz_attivi, paz_restituiti, paz_da_assegnare]
    })



#GESTIONE PAZIENTI

#Permette la visualizzazione della lista pazienti (GET)
#e la creazione manuale di una nuova anagrafica (POST).
@main_bp.route('/pazienti', methods=['GET', 'POST'])
@login_required
def gestisci_pazienti():
    if request.method == 'POST':
        paziente_id = request.form.get('id')
        
        #Applicazione di valori di default se i campi non sono compilati
        fuso_orario = request.form.get('fuso_orario') or 'Europe / Rome'
        nazione = request.form.get('nazione') or 'IT'
        data_attivazione = request.form.get('data_attivazione') or datetime.utcnow().strftime('%Y-%m-%d')

        esistente = Paziente.query.get(paziente_id)
        if esistente:
            flash(f"Attenzione: Il paziente {paziente_id} e' gia presente nel sistema.", "warning")
        else:
            nuovo_paziente = Paziente(
                id=paziente_id,
                regione=request.form.get('regione'),
                provincia=request.form.get('provincia'),
                latitudine=request.form.get('latitudine'),
                longitudine=request.form.get('longitudine'),
                fuso_orario=fuso_orario,
                nazione=nazione,
                data_attivazione=data_attivazione
            )
            db.session.add(nuovo_paziente)
            db.session.commit()
            flash(f"Paziente {paziente_id} creato con successo!", "success")
            
        return redirect(url_for('main.gestisci_pazienti'))

    lista_pazienti = Paziente.query.all()
    
    # Calcolo dinamico dello stato per le label colorate in tabella
    for p in lista_pazienti:
        assegnazione_attiva = Assegnazione.query.filter_by(paziente_id=p.id, data_restituzione=None).first()
        storico_assegnazioni = Assegnazione.query.filter_by(paziente_id=p.id).count()
        
        if assegnazione_attiva: p.stato_calcolato = "Attivo"
        elif storico_assegnazioni > 0: p.stato_calcolato = "Restituito"
        else: p.stato_calcolato = "Da Assegnare"
            
    return render_template('pazienti.html', pazienti=lista_pazienti, username=session.get('username'))


#Mostra la scheda dettagliata di un singolo paziente.
#Aggrega dati anagrafici, logistici (hardware) per la visualizzazione.
#La biometria viene caricata asincronamente tramite le rotte API.
@main_bp.route('/paziente/<string:id>')
@login_required
def profilo_paziente(id):
    paziente = Paziente.query.get_or_404(id)
    
    assegnazione = Assegnazione.query.filter_by(paziente_id=id, data_restituzione=None).first()
    storico_assegnazioni = Assegnazione.query.filter_by(paziente_id=paziente.id).count()
    
    if assegnazione: paziente.stato_calcolato = "Attivo"
    elif storico_assegnazioni > 0: paziente.stato_calcolato = "Restituito"
    else: paziente.stato_calcolato = "Da Assegnare"
    
    dispositivo_obj = Dispositivo.query.get(assegnazione.dispositivo_id) if assegnazione else None
    
    return render_template('profilo.html', 
                           paziente=paziente,
                           dispositivo=dispositivo_obj.id if dispositivo_obj else "Nessuno",
                           dispositivo_obj=dispositivo_obj,
                           data_assegnazione=assegnazione.data_assegnazione.strftime('%d/%m/%Y') if assegnazione else "N/A",
                           username=session.get('username'))


#Aggiorna i dati anagrafici e logistici di un paziente.
@main_bp.route('/paziente/<string:id>/modifica', methods=['POST'])
@login_required
def modifica_paziente(id):
    paziente = Paziente.query.get_or_404(id)
    paziente.nazione = request.form.get('nazione')
    paziente.regione = request.form.get('regione')
    paziente.provincia = request.form.get('provincia')
    paziente.fuso_orario = request.form.get('fuso_orario')
    paziente.data_attivazione = request.form.get('data_attivazione')
    
    #Conversione sicura delle coordinate in Float
    lat, lon = request.form.get('latitudine'), request.form.get('longitudine')
    
    if lat:
        try: paziente.latitudine = float(lat)
        except ValueError: pass
    else: paziente.latitudine = None

    if lon:
        try: paziente.longitudine = float(lon)
        except ValueError: pass
    else: paziente.longitudine = None

    db.session.commit()
    flash("Profilo logistico aggiornato con successo!", "success")
    return redirect(url_for('main.profilo_paziente', id=id))


#Hard delete di un paziente dal database.
#Implementa logica di sicurezza: prima di eliminare il paziente,
#scollega eventuali hardware a lui associati rendendoli nuovamente disponibili.
#I dati biometrici e lo storico verranno eliminati automaticamente in cascade da SQLAlchemy.
@main_bp.route('/paziente/<string:id>/elimina', methods=['POST'])
@login_required
def elimina_paziente(id):
    paziente = Paziente.query.get_or_404(id)
    
    assegnazioni = Assegnazione.query.filter_by(paziente_id=id).all()
    for ass in assegnazioni:
        # Liberazione forzata dell'hardware
        dispositivo = Dispositivo.query.get(ass.dispositivo_id)
        if dispositivo:
            dispositivo.stato = "Disponibile"
        db.session.delete(ass)
        
    db.session.delete(paziente)
    db.session.commit()
    
    flash(f"Paziente {id} e storico eliminati. Hardware sbloccato.", "success")
    return redirect(url_for('main.gestisci_pazienti'))



#UPLOAD DATI E AUTO-PROVISIONING

#Gestisce il caricamento del file ZIP di Google Takeout.
#Salva il file in una directory temporanea, invoca l'estrazione
#su 'utils.py' e successivamente ripulisce il file temporaneo.
@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('file')

        if not file:
            flash("Errore: Seleziona un file ZIP.", "danger")
            return redirect(url_for('main.upload'))

        filepath = os.path.join('/tmp', file.filename)
        file.save(filepath)
        
        #Invio all'engine di estrazione dati e biometria
        successo, messaggio, paziente_id = processa_file_zip(filepath)
        
        #Pulizia memoria
        if os.path.exists(filepath):
            os.remove(filepath)

        return render_template('upload_result.html', 
                               messaggio=messaggio, 
                               paziente_id=paziente_id if successo else None,
                               username=session.get('username'))
    
    return render_template('upload.html', username=session.get('username'))



#GESTIONE DISPOSITIVI HARDWARE

#Visualizza il magazzino hardware e permette l'inserimento manuale.
@main_bp.route('/dispositivi', methods=['GET', 'POST'])
@login_required
def gestisci_dispositivi():
    if request.method == 'POST':
        dispositivo_id = request.form.get('id')
        esistente = Dispositivo.query.get(dispositivo_id)
        
        if esistente:
            flash(f"Il dispositivo {dispositivo_id} esiste gia nel sistema.", "warning")
        else:
            nuovo_dispositivo = Dispositivo(
                id=dispositivo_id,
                modello=request.form.get('modello', 'Fitbit Inspire 3'),
                stato=request.form.get('stato', 'Disponibile'),
                batteria=request.form.get('batteria') 
            )
            db.session.add(nuovo_dispositivo)
            db.session.commit()
            flash("Dispositivo aggiunto con successo!", "success")
            
        return redirect(url_for('main.gestisci_dispositivi'))

    return render_template('dispositivi.html', dispositivi=Dispositivo.query.all(), username=session.get('username'))


#Aggiorna i parametri diagnostici del dispositivo.
#Include logica di allarme: se la batteria viene impostata a 0, il sistema 
#genera avvisi differenti in base allo stato logistico attuale.
   
@main_bp.route('/dispositivo/<string:id>/modifica', methods=['POST'])
@login_required
def modifica_dispositivo(id):
    dispositivo = Dispositivo.query.get_or_404(id)
    nuovo_stato = request.form.get('stato')
    batteria_nuova = request.form.get('batteria')
    
    # Previene modifiche di stato forzate su dispositivi attualmente indossati
    if nuovo_stato and dispositivo.stato not in ['In Uso', 'Assegnato']:
        dispositivo.stato = nuovo_stato
    
    avviso_critico = False
    dispositivo.modello = request.form.get('modello')
    
    if batteria_nuova:
        dispositivo.batteria = batteria_nuova
        # Trigger Allarmi Batteria
        if int(batteria_nuova) == 0:
            avviso_critico = True
            if dispositivo.stato in ['Assegnato', 'In Uso']:
                flash(f"CRITICITA': Batteria 0% per il dispositivo {id} in uso. Contattare il paziente.", "danger")
            elif dispositivo.stato == 'Disponibile':
                flash(f"AVVISO LOGISTICO: Dispositivo {id} Disponibile ma scarico. Mettere in carica.", "warning")
            elif dispositivo.stato == 'Manutenzione':
                flash(f"Nota: Il dispositivo in manutenzione {id} ha la batteria scarica.", "info")
    else:
        dispositivo.batteria = None
        
    db.session.commit()
    
    if not avviso_critico:
        flash(f"Dati del dispositivo {id} aggiornati con successo.", "success")
        
    return redirect(url_for('main.gestisci_dispositivi'))


#Elimina fisicamente un dispositivo dal magazzino e il suo storico associato.
#Intercettato dal controllo di sicurezza se il braccialetto è in uso.   
@main_bp.route('/dispositivo/<string:id>/elimina', methods=['POST'])
@login_required
def elimina_dispositivo(id):
    dispositivo = Dispositivo.query.get_or_404(id)
    if dispositivo.stato in ['Assegnato', 'In Uso']:
        flash(f"Operazione negata: dispositivo {id} attualmente in uso.", "danger")
        return redirect(url_for('main.gestisci_dispositivi'))

    # Pulizia orfani manuale dello storico prima di cancellare l'hardware
    Assegnazione.query.filter_by(dispositivo_id=id).delete()
    db.session.delete(dispositivo)
    db.session.commit()

    flash(f"Il dispositivo {id} e' stato rimosso definitivamente.", "success")
    return redirect(url_for('main.gestisci_dispositivi'))


#Mostra la cronologia completa dei portatori (pazienti) per uno specifico hardware.  
@main_bp.route('/dispositivo/<string:id>/storico')
@login_required
def storico_dispositivo(id):
    dispositivo = Dispositivo.query.get_or_404(id)
    assegnazioni_db = Assegnazione.query.filter_by(dispositivo_id=id).order_by(Assegnazione.data_assegnazione.desc()).all()
    
    storico = []
    for ass in assegnazioni_db:
        paziente = Paziente.query.get(ass.paziente_id)
        storico.append({
            'paziente_id': paziente.id if paziente else 'Sconosciuto',
            'regione': paziente.regione if paziente else 'N/D',
            'data_inizio': ass.data_assegnazione.strftime('%d/%m/%Y') if ass.data_assegnazione else "N/D",
            'data_fine': ass.data_restituzione.strftime('%d/%m/%Y') if ass.data_restituzione else "In Corso",
            'stato_assegnazione': 'Conclusa' if ass.data_restituzione else 'Attiva'
        })
        
    return render_template('storico_dispositivo.html', dispositivo=dispositivo, storico=storico, username=session.get('username'))



#GESTIONE ASSEGNAZIONI

#Gestione delle operazioni di Consegna e Restituzione.
#Ci assicuriamo che un paziente non abbia due tracker e che i braccialetti scarichi non vengano consegnati.
@main_bp.route('/assegnazioni', methods=['GET', 'POST'])
@login_required
def gestisci_assegnazioni():

    if request.method == 'POST':
        azione = request.form.get('azione')

        if azione == 'assegna':
            paziente_id, dispositivo_id = request.form.get('paziente_id'), request.form.get('dispositivo_id')
            dispositivo = Dispositivo.query.get(dispositivo_id)
            
            # Blocco di sicurezza hardware
            if dispositivo and dispositivo.batteria is not None and int(dispositivo.batteria) <= 0:
                flash(f"Errore: Dispositivo {dispositivo_id} ha batteria allo 0%.", "danger")
            else:
                # Blocco di sicurezza anagrafica
                if Assegnazione.query.filter_by(paziente_id=paziente_id, data_restituzione=None).first():
                    flash(f"Attenzione: Il paziente {paziente_id} ha gia un dispositivo in uso!", "warning")
                else:
                    db.session.add(Assegnazione(paziente_id=paziente_id, dispositivo_id=dispositivo_id))
                    if dispositivo: dispositivo.stato = 'Assegnato'
                    db.session.commit()
                    flash("Dispositivo assegnato con successo!", "success")

        elif azione == 'restituisci':
            assegnazione = Assegnazione.query.get(request.form.get('assegnazione_id'))
            if assegnazione and not assegnazione.data_restituzione:
                assegnazione.data_restituzione = datetime.utcnow() # Chiusura assegnazione
                dispositivo = Dispositivo.query.get(assegnazione.dispositivo_id)
                if dispositivo: dispositivo.stato = 'Disponibile' # Rientro a magazzino
                db.session.commit()
                flash("Dispositivo restituito e nuovamente disponibile.", "info")

        return redirect(url_for('main.gestisci_assegnazioni'))

    # Dati per la vista: escludiamo i pazienti che hanno gia hardware
    assegnazioni_attive = Assegnazione.query.filter_by(data_restituzione=None).all()
    pazienti_occupati = [a.paziente_id for a in assegnazioni_attive]
    
    pazienti_idonei = Paziente.query.filter(~Paziente.id.in_(pazienti_occupati)).all() if pazienti_occupati else Paziente.query.all()
    
    return render_template('assegnazioni.html', 
                           pazienti=pazienti_idonei, 
                           dispositivi=Dispositivo.query.filter_by(stato='Disponibile').all(), 
                           assegnazioni=assegnazioni_attive, 
                           username=session.get('username'))


#API DATI BIOMETRICI E STATISTICHE

#Estrae le ultime 5 rilevazioni giornaliere. (Requisito degli ultimi 5 giorni)
#I dati vengono formattati in array paralleli pronti per il parsing da parte di Chart.js.
#Recupera in ordine discendente (piu recenti prima) limitando a 5
@main_bp.route('/api/paziente/<string:id>/biometrici')
@login_required
def api_biometrici_paziente(id):
    dati_db = DatoBiometricoGiornaliero.query.filter_by(paziente_id=id).order_by(DatoBiometricoGiornaliero.data_registrazione.desc()).limit(5).all()
    
    #Inverte per disegnare il grafico in ordine cronologico corretto (da sinistra a destra)
    dati_db.reverse()
    
    risultato = {'date': [], 'battito': [], 'spo2': [], 'passi': [], 'attivita': [], 'sonno': []}
    for record in dati_db:
        risultato['date'].append(record.data_registrazione)
        risultato['battito'].append(record.frequenza_cardiaca_media)
        risultato['spo2'].append(record.spo2_media)
        risultato['passi'].append(record.passi_totali)
        risultato['attivita'].append(record.minuti_attivita)
        risultato['sonno'].append(record.minuti_sonno)
        
    return jsonify(risultato)


#Estrae lo storico clinico completo del paziente per la visuale approfondita.
#Stessa struttura dati della route dei 5 giorni, ma senza limiti di query.
@main_bp.route('/api/paziente/<string:id>/biometrici_completi')
@login_required
def api_biometrici_completi_paziente(id):

    dati_db = DatoBiometricoGiornaliero.query.filter_by(paziente_id=id).order_by(DatoBiometricoGiornaliero.data_registrazione.asc()).all()
    
    risultato = {'date': [], 'battito': [], 'spo2': [], 'passi': [], 'attivita': [], 'sonno': []}
    for record in dati_db:
        risultato['date'].append(record.data_registrazione)
        risultato['battito'].append(record.frequenza_cardiaca_media)
        risultato['spo2'].append(record.spo2_media)
        risultato['passi'].append(record.passi_totali)
        risultato['attivita'].append(record.minuti_attivita)
        risultato['sonno'].append(record.minuti_sonno)
        
    return jsonify(risultato)