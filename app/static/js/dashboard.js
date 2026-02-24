document.addEventListener("DOMContentLoaded", function () {

    var map = L.map('mappa_italia').setView([41.8719, 12.5674], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    var iconaVerde = new L.Icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
    });

    var iconaGrigia = new L.Icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-grey.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]
    });

    fetch('/api/dashboard_data')
        .then(response => response.json())
        .then(data => {

            data.pazienti.forEach(function (paziente) {
                var icona = paziente.ha_dispositivo ? iconaVerde : iconaGrigia;
                var marker = L.marker([paziente.lat, paziente.lng], { icon: icona }).addTo(map);

                marker.bindPopup(
                    "<b>ID Paziente:</b> " + paziente.id + "<br>" +
                    "<b>Dispositivo:</b> " + paziente.dispositivo_id + "<br>" +
                    "<b>Assegnato il:</b> " + paziente.data_assegnazione
                );
            });

            var ctxRegioni = document.getElementById('graficoRegioni');
            if (ctxRegioni) {
                new Chart(ctxRegioni.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: data.regioni_nomi,
                        datasets: [{
                            label: 'Numero Pazienti',
                            data: data.regioni_valori,
                            backgroundColor: 'rgba(54, 162, 235, 0.6)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
                    }
                });
            }

            var ctxPazienti = document.getElementById('graficoStatoPazienti');
            if (ctxPazienti) {
                new Chart(ctxPazienti.getContext('2d'), {
                    type: 'doughnut',
                    data: {
                        labels: ['Attivi', 'Restituiti', 'Da Assegnare'],
                        datasets: [{
                            data: data.stati_pazienti,
                            backgroundColor: [
                                '#198754',
                                '#6c757d',
                                '#ffc107'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'bottom'
                            }
                        }
                    }
                });
            }
        })
        .catch(error => console.error("Errore nel caricamento dei dati della dashboard:", error));
});