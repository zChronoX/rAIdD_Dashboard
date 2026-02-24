
# Import per l'estrazione dei dati
import zipfile
import csv
import io
import json
import re
from datetime import datetime

# Importazione dei modelli del database
from .models import db, Paziente, Dispositivo, Assegnazione, DatoBiometricoGiornaliero

# FUNZIONI HELPER DI FORMATTAZIONE 




#Converte la stringa della data di sincronizzazione dal formato ISO di Fitbit
#(es. 2024-12-03T14:30:00.000) a un formato europeo piu leggibile (GG/MM/AAAA HH:MM).
def formatta_data_sync(iso_string):
    if not iso_string:
        return None
    try:
        clean_str = iso_string.split('.')[0]
        dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_string


#Migliora la leggibilita' del fuso orario rimuovendo underscore 
#e aggiungendo spazi (es. 'Europe/Rome' diventa 'Europe / Rome').
def formatta_fuso_orario(tz_string):
    if not tz_string:
        return None
    return tz_string.replace('/', ' / ').replace('_', ' ')


#Metodo principale per l'elaborazione del file ZIP
#Esegue il parsing del file ZIP di Google Takeout.
#E' divisa in 5 fasi:
#1. Identificazione: Trova il profilo utente.
#2. Anagrafica: Crea o aggiorna il record Paziente.
#3. Hardware: Cerca le info sul dispositivo accoppiato.
#4. Auto-Provisioning: Assegna il dispositivo risolvendo eventuali conflitti.
#5. Biometria: Aggrega e salva i dati clinici giornalieri. 
#Restituisce: (Successo_Booleano, Messaggio_Di_Stato, Paziente_ID)
def processa_file_zip(filepath):

    try:
        paziente_id = None
        dati_estratti = {}


        #FASE 1: LETTURA PROFILO E IDENTIFICAZIONE

        # Apriamo lo ZIP in sola lettura e cerchiamo il file 'profile.csv'
        with zipfile.ZipFile(filepath, 'r') as z:
            for filename in z.namelist():
                if 'profile.csv' in filename.lower():
                    with z.open(filename) as f:
                        # Convertiamo i byte in testo leggibile per il modulo CSV
                        content = io.TextIOWrapper(f, encoding='utf-8')
                        reader = csv.DictReader(content)
                        for row in reader:
                            paziente_id = row.get('id')
                            dati_estratti['regione'] = row.get('state')
                            dati_estratti['provincia'] = row.get('city')
                            dati_estratti['nazione'] = row.get('country')
                            dati_estratti['fuso_orario'] = formatta_fuso_orario(row.get('timezone'))
                            dati_estratti['data_attivazione'] = row.get('member_since')
                            break # Ci basta la prima (e unica) riga del profilo
                    break

        # Se non troviamo un ID, lo ZIP e' invalido o non e' di Fitbit
        if not paziente_id:
            return False, "Errore: File Profile.csv non trovato nello ZIP. Impossibile identificare l'utente.", None


        #FASE 2: CREAZIONE O AGGIORNAMENTO ANAGRAFICA
        paziente = db.session.get(Paziente, paziente_id)
        nuovo_utente = False

        def pulisci_dato(valore):
            """Evita che stringhe testuali come 'null' vengano salvate nel DB come testo valido."""
            if valore and str(valore).lower() != 'null':
                return valore
            return None

        regione_pulita = pulisci_dato(dati_estratti.get('regione'))
        provincia_pulita = pulisci_dato(dati_estratti.get('provincia'))
        nazione_pulita = pulisci_dato(dati_estratti.get('nazione'))
        fuso_pulito = pulisci_dato(dati_estratti.get('fuso_orario'))
        data_att_pulita = pulisci_dato(dati_estratti.get('data_attivazione'))

        # Se il paziente non esiste, lo creiamo da zero passando tutti i parametri
        if not paziente:
            paziente = Paziente(
                id=paziente_id,
                regione=regione_pulita,
                provincia=provincia_pulita,
                nazione=nazione_pulita,
                fuso_orario=fuso_pulito,
                data_attivazione=data_att_pulita
            )
            db.session.add(paziente)
            nuovo_utente = True
        # Se esiste gia', aggiorniamo solo i campi che abbiamo effettivamente trovato nello ZIP
        else:
            if regione_pulita: paziente.regione = regione_pulita
            if provincia_pulita: paziente.provincia = provincia_pulita
            if nazione_pulita: paziente.nazione = nazione_pulita
            if fuso_pulito: paziente.fuso_orario = fuso_pulito
            if data_att_pulita: paziente.data_attivazione = data_att_pulita

        db.session.commit()


        #FASE 3: RICERCA HARDWARE
        info_hardware = None
        hardware_id = None
        batteria = None
        ultima_sync = None
        data_aggiunta_reale = None
        
        # Scansioniamo nuovamente lo ZIP alla ricerca dei file sui dispositivi accoppiati
        with zipfile.ZipFile(filepath, 'r') as z:
            for filename in z.namelist():
                nome_file = filename.lower()
                
                # Priorita' 1: File 'trackers.csv' (contiene info su batteria e sync)
                if 'paired devices/trackers.csv' in nome_file:
                    try:
                        with z.open(filename) as f:
                            content = io.TextIOWrapper(f, encoding='utf-8')
                            reader = csv.DictReader(content)
                            for row in reader:
                                info_hardware = row.get('device_type')
                                hardware_id = row.get('tracker_id')
                                batteria = row.get('batt_level')
                                ultima_sync = formatta_data_sync(row.get('last_sync_date_time'))
                                data_aggiunta_reale = row.get('date_added')
                                if info_hardware: break
                    except Exception:
                        continue
                
                # Priorita' 2: File 'devices.csv' (fallback se trackers.csv non e' presente)
                elif 'paired devices/devices.csv' in nome_file and not info_hardware:
                    try:
                        with z.open(filename) as f:
                            content = io.TextIOWrapper(f, encoding='utf-8')
                            reader = csv.DictReader(content)
                            for row in reader:
                                info_hardware = row.get('device_type')
                                hardware_id = row.get('wire_id')
                                if info_hardware: break
                    except Exception:
                        continue


        #FASE 4: AUTO-PROVISIONING E BLOCCHI DI SICUREZZA
        msg_azione = "Creato nuovo profilo logistico" if nuovo_utente else "Aggiornato profilo esistente"
        messaggio_finale = f"{msg_azione} per ID {paziente_id}. Dati sincronizzati."

        if info_hardware:
            # Se manca l'ID hardware (caso raro), ne generiamo uno di fallback
            id_dispositivo_finale = hardware_id if hardware_id else f"DEV-{paziente_id}"
            
            # Recupera o crea il Dispositivo a magazzino, popolando tutti i dati
            dispositivo = db.session.get(Dispositivo, id_dispositivo_finale)
            if not dispositivo:
                dispositivo = Dispositivo(
                    id=id_dispositivo_finale, 
                    modello=info_hardware, 
                    stato="In Uso",
                    batteria=batteria,
                    ultima_sincronizzazione=ultima_sync
                )
                db.session.add(dispositivo)
            else:
                if batteria: dispositivo.batteria = batteria
                if ultima_sync: dispositivo.ultima_sincronizzazione = ultima_sync
            
            #Controlliamo che il dispositivo non sia in Manutenzione
            if dispositivo.stato == 'Manutenzione':
                messaggio_finale += f" ATTENZIONE: Hardware {info_hardware} rilevato, ma risulta attualmente in MANUTENZIONE. L'assegnazione automatica e' stata annullata. Ripristinare il dispositivo dal magazzino prima di poterlo assegnare."
            else:
                #Controlliamo che il dispositivo non sia assegnato a UN ALTRO paziente
                assegnazioni_altri = Assegnazione.query.filter_by(dispositivo_id=id_dispositivo_finale, data_restituzione=None).all()
                conflitto_proprietario = None
                
                for ass in assegnazioni_altri:
                    if ass.paziente_id != paziente_id:
                        conflitto_proprietario = ass.paziente_id
                        break

                if conflitto_proprietario:
                    messaggio_finale += f" ATTENZIONE: Hardware {info_hardware} rilevato, ma risulta attualmente in carico al paziente {conflitto_proprietario}. L'assegnazione automatica e' stata annullata. Effettuare la restituzione manuale prima di riassegnarlo."
                else:
                    #Controlliamo le vecchie assegnazioni
                    #Se il paziente aveva altri dispositivi, li chiudiamo per evitare doppi tracker
                    assegnazioni_vecchie_paz = Assegnazione.query.filter_by(paziente_id=paziente_id, data_restituzione=None).all()
                    for ass in assegnazioni_vecchie_paz:
                        if ass.dispositivo_id != id_dispositivo_finale:
                            ass.data_restituzione = datetime.utcnow()
                            vecchio_disp = db.session.get(Dispositivo, ass.dispositivo_id)
                            # Riportiamo a magazzino il vecchio dispositivo (se non era rotto)
                            if vecchio_disp and vecchio_disp.stato != 'Manutenzione':
                                vecchio_disp.stato = "Disponibile"

                    # Creazione dell'assegnazione effettiva
                    dispositivo.stato = "In Uso"
                    assegnazione_corrente = Assegnazione.query.filter_by(
                        paziente_id=paziente_id, 
                        dispositivo_id=id_dispositivo_finale, 
                        data_restituzione=None
                    ).first()

                    if not assegnazione_corrente:
                        data_ass_obj = datetime.utcnow()
                        if data_aggiunta_reale:
                            try:
                                data_ass_obj = datetime.strptime(data_aggiunta_reale, "%Y-%m-%d")
                            except Exception:
                                pass
                                
                        nuova_assegnazione = Assegnazione(
                            paziente_id=paziente_id,
                            dispositivo_id=id_dispositivo_finale,
                            data_assegnazione=data_ass_obj
                        )
                        db.session.add(nuova_assegnazione)
                        
                        # Trigger Alert Batteria post-creazione
                        if batteria and int(batteria) <= 5:
                            messaggio_finale += f" Hardware {info_hardware} registrato. ATTENZIONE: Livello batteria critico ({batteria}%). Avvisare il paziente."
                        else:
                            messaggio_finale += f" Hardware {info_hardware} registrato e assegnato con successo."
                    else:
                        # Trigger Alert Batteria post-aggiornamento
                        if batteria and int(batteria) <= 5:
                            messaggio_finale += f" Hardware {info_hardware} aggiornato. ATTENZIONE: Livello batteria critico ({batteria}%)."
                        else:
                            messaggio_finale += f" Hardware {info_hardware} aggiornato."

            db.session.commit()


        #FASE 5: ESTRAZIONE DATI BIOMETRICI
        #Questo blocco parsa silenziosamente i JSON/CSV medici, aggrega i dati 
        #giorno per giorno ed estrae le medie per preparare il database ai grafici.
        try:
            daily_stats = {} # Dizionario per aggregare i dati per data (YYYY-MM-DD)
            
            def get_day(date_str):
                """Inizializza una nuova giornata nel dizionario se non esiste."""
                if date_str not in daily_stats:
                    daily_stats[date_str] = {'hr_sum': 0, 'hr_count': 0, 'spo2': None, 'steps': 0, 'sleep': 0, 'activity': 0}
                return daily_stats[date_str]

            with zipfile.ZipFile(filepath, 'r') as z:
                for filename in z.namelist():
                    nome_low = filename.lower()
                    
                    # Estrazione Frequenza Cardiaca (Da JSON, accumula per calcolare la media)
                    if 'global export data/heart_rate-' in nome_low and nome_low.endswith('.json'):
                        match = re.search(r'heart_rate-(\d{4}-\d{2}-\d{2})', nome_low)
                        if match:
                            date_str = match.group(1)
                            try:
                                data = json.loads(z.read(filename).decode('utf-8'))
                                day_d = get_day(date_str)
                                for entry in data:
                                    val = entry.get('value', {})
                                    bpm = val.get('bpm') if isinstance(val, dict) else None
                                    if bpm:
                                        day_d['hr_sum'] += bpm
                                        day_d['hr_count'] += 1
                            except Exception: pass
                    
                    # Estrazione Passi (Da JSON, somma totale)
                    elif 'global export data/steps-' in nome_low and nome_low.endswith('.json'):
                        match = re.search(r'steps-(\d{4}-\d{2}-\d{2})', nome_low)
                        if match:
                            date_str = match.group(1)
                            try:
                                data = json.loads(z.read(filename).decode('utf-8'))
                                day_d = get_day(date_str)
                                for entry in data:
                                    day_d['steps'] += int(entry.get('value', 0))
                            except Exception: pass
                            
                    # Estrazione Sonno (Da JSON, somma minuti totali di riposo)
                    elif 'global export data/sleep-' in nome_low and nome_low.endswith('.json'):
                        try:
                            data = json.loads(z.read(filename).decode('utf-8'))
                            for entry in data:
                                date_str = entry.get('dateOfSleep')
                                if date_str:
                                    day_d = get_day(date_str)
                                    day_d['sleep'] += int(entry.get('minutesAsleep', 0))
                        except Exception: pass
                    
                    # Estrazione Attivita' Fisica (Da JSON, somma minuti moderati e intensi)
                    elif 'global export data/very_active_minutes-' in nome_low or 'global export data/moderately_active_minutes-' in nome_low:
                        match = re.search(r'active_minutes-(\d{4}-\d{2}-\d{2})', nome_low)
                        if match:
                            date_str = match.group(1)
                            try:
                                data = json.loads(z.read(filename).decode('utf-8'))
                                day_d = get_day(date_str)
                                for entry in data:
                                    day_d['activity'] += int(entry.get('value', 0))
                            except Exception: pass
                    
                    # Estrazione SpO2 (Da CSV riepilogativo di Google)
                    elif 'oxygen saturation (spo2)/daily spo2' in nome_low and nome_low.endswith('.csv'):
                        try:
                            content = io.TextIOWrapper(z.open(filename), encoding='utf-8')
                            reader = csv.DictReader(content)
                            for row in reader:
                                raw_date = row.get('timestamp') or row.get('date') or list(row.values())[0]
                                if raw_date and len(raw_date) >= 10:
                                    date_str = raw_date[:10]
                                    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                                        day_d = get_day(date_str)
                                        # Il CSV di Google ha formattazioni variabili, proviamo le chiavi piu comuni
                                        val = row.get('average_value') or list(row.values())[1]
                                        try:
                                            day_d['spo2'] = float(val)
                                        except ValueError:
                                            pass
                        except Exception: pass

            # Elimina lo storico clinico precedente per questo utente per evitare doppioni
            DatoBiometricoGiornaliero.query.filter_by(paziente_id=paziente_id).delete()
            
            # Scrittura nel Database dei dati aggregati
            for date_str, stats in sorted(daily_stats.items()):
                # Salviamo il giorno solo se c'e' stato almeno un battito registrato o dei passi
                if stats['hr_count'] > 0 or stats['steps'] > 0 or stats['sleep'] > 0:
                    hr_media = round(stats['hr_sum'] / stats['hr_count'], 1) if stats['hr_count'] > 0 else None
                    
                    nuovo_dato = DatoBiometricoGiornaliero(
                        paziente_id=paziente_id,
                        data_registrazione=date_str,
                        frequenza_cardiaca_media=hr_media,
                        spo2_media=stats['spo2'],
                        passi_totali=stats['steps'],
                        minuti_attivita=stats['activity'],
                        minuti_sonno=stats['sleep']
                    )
                    db.session.add(nuovo_dato)
            
            db.session.commit()
            
        except Exception as err:
            print(f"Errore durante l'estrazione dei dati biometrici: {err}")
            db.session.rollback()

        return True, "SUCCESSO! " + messaggio_finale, paziente_id

    except Exception as e:
        db.session.rollback()
        return False, f"Errore critico di sistema durante il parsing dello ZIP: {str(e)}", None