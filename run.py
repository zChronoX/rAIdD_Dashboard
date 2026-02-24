
# ENTRY-POINT DELL'APPLICAZIONE
from app import create_app

# Istanzia l'applicazione utilizzando il pattern Application Factory
app = create_app()

if __name__ == '__main__':
    # L'host '0.0.0.0' e' fondamentale per Docker: 
    # permette al server Flask di esporre la porta verso l'esterno del container.
    # Il flag debug=True abilita il ricaricamento automatico in fase di sviluppo.
    app.run(host='0.0.0.0', port=5000, debug=True)