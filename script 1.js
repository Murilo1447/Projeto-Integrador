// Redirecionamento
function irParaDenuncias() {
    window.location.href = "denuncias.html";
  }
  
  // Mapa
  var map = L.map('map').setView([-23.5505, -46.6333], 12);
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
  }).addTo(map);
  
  // Função para marcadores
  function addMarker(lat, lng, color) {
    L.circleMarker([lat, lng], {
      radius: 8,
      fillColor: color,
      color: "#000",
      weight: 1,
      fillOpacity: 0.8
    }).addTo(map);
  }
  
  // Exemplos
  addMarker(-23.55, -46.63, "green");
  addMarker(-23.56, -46.62, "yellow");
  addMarker(-23.57, -46.64, "red");