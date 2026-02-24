document.addEventListener("DOMContentLoaded", function () {
    var container = document.getElementById('chartsContainer');
    if (!container) return;

    var pazienteId = container.getAttribute('data-id');

    // --- FUNZIONI DI UTILITY GLOBALI ---
    function calcolaMediaDecimale(array) {
        let validi = array.filter(v => v != null && v > 0);
        if (validi.length === 0) return "N/D";
        return (validi.reduce((a, b) => a + b, 0) / validi.length).toFixed(1);
    }

    function calcolaMediaIntera(array) {
        let validi = array.filter(v => v != null && v > 0);
        if (validi.length === 0) return "0";
        return Math.round(validi.reduce((a, b) => a + b, 0) / validi.length);
    }

    // ==========================================
    // PARTE 1: GRAFICI SEPARATI 5 GIORNI
    // ==========================================
    fetch('/api/paziente/' + pazienteId + '/biometrici')
        .then(response => response.json())
        .then(data => {
            if (!data.date || data.date.length === 0) {
                container.classList.add('d-none');
                document.getElementById('noDataAlert').classList.remove('d-none');
                return;
            }

            // Popolamento dei Badge in HTML (5 Giorni)
            document.getElementById('avgBpm').innerText = calcolaMediaDecimale(data.battito);
            let spo2Media = calcolaMediaDecimale(data.spo2);
            document.getElementById('avgSpo2').innerText = spo2Media !== "N/D" ? spo2Media + "%" : "N/D";
            document.getElementById('avgPassi').innerText = calcolaMediaIntera(data.passi);
            document.getElementById('avgAttivita').innerText = calcolaMediaIntera(data.attivita);
            document.getElementById('avgSonno').innerText = calcolaMediaIntera(data.sonno);

            // Disegno Grafici Separati (5 Giorni)
            // Parametri: CanvasID, Date, Dati, Titolo, Colore Linea/Pallini, Colore Sfondo, Asse Y, Tratteggiata
            disegnaGraficoLineaGenerico('chartBPM', data.date, data.battito, 'Frequenza (BPM)', 'rgba(220, 53, 69, 1)', 'rgba(220, 53, 69, 0.1)', 'BPM');
            disegnaGraficoLineaGenerico('chartSpO2', data.date, data.spo2, 'SpO2 (%)', 'rgba(13, 110, 253, 1)', 'transparent', '%', true);
            disegnaGraficoBarreGenerico('chartPassi', data.date, data.passi, 'Passi Totali', 'rgba(25, 135, 84, 0.6)', 'Passi');
            disegnaGraficoLineaGenerico('chartMinutiAttivi', data.date, data.attivita, 'Minuti Attivi', 'rgba(255, 193, 7, 1)', 'rgba(255, 193, 7, 0.2)', 'Minuti');
            disegnaGraficoBarreGenerico('chartSonno', data.date, data.sonno, 'Minuti di Sonno', 'rgba(111, 66, 193, 0.6)', 'Minuti');
        })
        .catch(error => console.error('Errore timeline 5 giorni:', error));

    // ==========================================
    // PARTE 2: STORICO COMPLETO SEPARATO NELLA MODALE
    // ==========================================
    var storicoCaricato = false;
    var modalElement = document.getElementById('modalStoricoCompleto');

    modalElement.addEventListener('shown.bs.modal', function () {
        if (storicoCaricato) return;

        fetch('/api/paziente/' + pazienteId + '/biometrici_completi')
            .then(response => response.json())
            .then(data => {
                document.getElementById('loaderStorico').classList.add('d-none');
                document.getElementById('containerStoricoCompleto').classList.remove('d-none');

                // Popolamento dei Badge in HTML (Storico Completo)
                document.getElementById('avgBpmCompleto').innerText = calcolaMediaDecimale(data.battito);
                let spo2MediaComp = calcolaMediaDecimale(data.spo2);
                document.getElementById('avgSpo2Completo').innerText = spo2MediaComp !== "N/D" ? spo2MediaComp + "%" : "N/D";
                document.getElementById('avgPassiCompleto').innerText = calcolaMediaIntera(data.passi);
                document.getElementById('avgAttivitaCompleta').innerText = calcolaMediaIntera(data.attivita);
                document.getElementById('avgSonnoCompleto').innerText = calcolaMediaIntera(data.sonno);

                // Disegno Grafici Separati (Storico Completo)
                disegnaGraficoLineaGenerico('chartBPMCompleto', data.date, data.battito, 'Frequenza (BPM)', 'rgba(220, 53, 69, 1)', 'rgba(220, 53, 69, 0.1)', 'BPM');
                disegnaGraficoLineaGenerico('chartSpO2Completo', data.date, data.spo2, 'SpO2 (%)', 'rgba(13, 110, 253, 1)', 'transparent', '%', true);
                disegnaGraficoBarreGenerico('chartPassiCompleto', data.date, data.passi, 'Passi Totali', 'rgba(25, 135, 84, 0.6)', 'Passi');
                disegnaGraficoLineaGenerico('chartMinutiAttiviCompleto', data.date, data.attivita, 'Minuti Attivi', 'rgba(255, 193, 7, 1)', 'rgba(255, 193, 7, 0.2)', 'Minuti');
                disegnaGraficoBarreGenerico('chartSonnoCompleto', data.date, data.sonno, 'Minuti di Sonno', 'rgba(111, 66, 193, 0.6)', 'Minuti');

                storicoCaricato = true;
            })
            .catch(error => console.error('Errore storico completo:', error));
    });

    // Funzione per grafici a linea (BPM, SpO2, Minuti Attivi)
    function disegnaGraficoLineaGenerico(canvasId, labels, dataValues, labelText, coloreBordo, coloreSfondo, yAxisTitle, isDashed = false) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: labelText,
                    data: dataValues,
                    borderColor: coloreBordo,
                    backgroundColor: coloreSfondo,
                    pointBackgroundColor: coloreBordo, // Pallini dello stesso colore della linea
                    pointBorderColor: '#ffffff', // Bordo bianco intorno al pallino per farlo risaltare
                    pointBorderWidth: 1,
                    pointRadius: 3, // Dimensione dei pallini
                    tension: 0.3, // Curvatura della linea
                    fill: !isDashed, // Riempie l'area sotto la linea se non e' tratteggiata
                    borderDash: isDashed ? [5, 5] : []
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: { display: true, text: yAxisTitle },
                        beginAtZero: yAxisTitle !== 'BPM' && yAxisTitle !== '%'
                    }
                }
            }
        });
    }

    // Funzione per grafici a barre (Passi, Sonno)
    function disegnaGraficoBarreGenerico(canvasId, labels, dataValues, labelText, coloreSfondo, yAxisTitle) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: labelText,
                    data: dataValues,
                    backgroundColor: coloreSfondo,
                    borderColor: coloreSfondo.replace('0.6', '1'), // Rende il bordo della barra pieno
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: { display: true, text: yAxisTitle },
                        beginAtZero: true
                    }
                }
            }
        });
    }
});