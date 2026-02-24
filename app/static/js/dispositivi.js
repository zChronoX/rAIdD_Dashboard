document.addEventListener("DOMContentLoaded", function () {
    // Trova tutte le barre della batteria nella pagina
    var barreBatteria = document.querySelectorAll('.barra-batteria');

    // Applica la larghezza in base all'attributo data-batteria
    barreBatteria.forEach(function (barra) {
        var livello = barra.getAttribute('data-batteria');
        if (livello) {
            barra.style.width = livello + '%';
        }
    });
});