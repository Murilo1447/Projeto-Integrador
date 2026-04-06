// Redirecionamento
function irParaDenuncias() {
  window.location.href = "denuncias.html";
}

// ======================
// MAPA
// ======================
var map = L.map('map', {
  zoomControl: false
}).setView([-23.5505, -46.6333], 12);

// adiciona o zoom no lado direito
L.control.zoom({
  position: 'topright'
}).addTo(map);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap'
}).addTo(map);

// ======================
// PAINEL DE COMENTÁRIOS
// ======================

// Criar painel lateral
const painel = L.control({ position: "topleft" });

painel.onAdd = function () {
  this._div = L.DomUtil.create("div", "painel-comentarios");
  this._div.style.width = "250px";
  this._div.style.maxHeight = "300px";
  this._div.style.overflowY = "auto";
  this._div.style.background = "white";
  this._div.style.padding = "10px";
  this._div.style.boxShadow = "0 0 10px rgba(0,0,0,0.3)";
  this._div.style.display = "none";
  return this._div;
};

painel.addTo(map);

// Função para abrir painel
function abrirComentarios(index) {
  const chamado = chamados[index];

  let comentariosHTML = "<h4>Comentários</h4>";

  if (chamado.comentarios && chamado.comentarios.length > 0) {
    chamado.comentarios.forEach(com => {
      comentariosHTML += `<p>• ${com}</p>`;
    });
  } else {
    comentariosHTML += "<p>Sem comentários.</p>";
  }

  comentariosHTML += `
    <input type="text" id="novoComentario" placeholder="Adicionar comentário" style="width:100%; margin-top:5px;">
    <button onclick="adicionarComentario(${index})" style="width:100%; margin-top:5px;">Enviar</button>
    <button onclick="fecharComentarios()" style="width:100%; margin-top:5px;">Fechar</button>
  `;

  painel._div.innerHTML = comentariosHTML;
  painel._div.style.display = "block";
}

// Função para fechar painel
function fecharComentarios() {
  painel._div.style.display = "none";
}

// Função para adicionar comentário
function adicionarComentario(index) {
  const input = document.getElementById("novoComentario");
  const texto = input.value.trim();

  if (!texto) return;

  if (!chamados[index].comentarios) {
    chamados[index].comentarios = [];
  }

  chamados[index].comentarios.push(texto);

  localStorage.setItem("chamados", JSON.stringify(chamados));

  abrirComentarios(index); // re-renderiza painel
}


// ======================
// Função marcador com popup
// ======================
function addMarker(lat, lng, color, popupContent) {

  L.circleMarker([lat, lng], {
    radius: 8,
    fillColor: color,
    color: "#000",
    weight: 1,
    fillOpacity: 0.8
  })
  .addTo(map)
  .bindPopup(popupContent);
}


// ======================
// Buscar latitude e longitude pelo endereço
// ======================
async function buscarCoordenadas(endereco) {

  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(endereco)}`;

  const response = await fetch(url);
  const data = await response.json();

  if (data.length > 0) {
    return {
      lat: parseFloat(data[0].lat),
      lng: parseFloat(data[0].lon)
    };
  }

  return null;
}


// ======================
// Carregar chamados do localStorage
// ======================
let chamados = JSON.parse(localStorage.getItem("chamados")) || [];


// ======================
// Renderizar chamados no mapa
// ======================
async function renderMapa() {

  for (let i = 0; i < chamados.length; i++) {

    let c = chamados[i];
    let cor;

    if (c.status === "Resolvido") cor = "green";
    else if (c.status === "Pendente") cor = "yellow";
    else cor = "red";

    if (!c.lat || !c.lng) {
      const coordenadas = await buscarCoordenadas(c.local);
      if (coordenadas) {
        c.lat = coordenadas.lat;
        c.lng = coordenadas.lng;
      } else {
        continue;
      }
    }

    const popupHTML = `
      <strong>${c.categoria}</strong><br>
      <strong>${c.nome}</strong><br>
      ${c.descricao}<br>
      ${c.local}<br>
      Status: ${c.status}<br><br>
      <button  onclick="abrirComentarios(${i})">
        Mostrar Comentários
      </button>
    `;

    addMarker(c.lat, c.lng, cor, popupHTML);
  }

  // Salva novamente com lat/lng
  localStorage.setItem("chamados", JSON.stringify(chamados));
}

renderMapa();

// ======================
// AUTOCOMPLETE DE ENDEREÇO
// ======================

const searchInput = document.querySelector(".search");

// Criar container de sugestões
const sugestoesBox = document.createElement("div");
sugestoesBox.classList.add("sugestoes-box");
document.querySelector(".search-container").appendChild(sugestoesBox);
sugestoesBox.style.position = "absolute";
sugestoesBox.style.background = "white";
sugestoesBox.style.width = searchInput.offsetWidth + "px";
sugestoesBox.style.maxHeight = "200px";
sugestoesBox.style.overflowY = "auto";
sugestoesBox.style.border = "1px solid #ccc";
sugestoesBox.style.zIndex = "1000";
sugestoesBox.style.display = "none";

searchInput.parentNode.appendChild(sugestoesBox);

let marcadorBusca = null;

// Buscar sugestões enquanto digita
searchInput.addEventListener("input", async function () {

  const texto = searchInput.value.trim();

  if (texto.length < 3) {
    sugestoesBox.style.display = "none";
    return;
  }

  const url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=5&q=${encodeURIComponent(texto)}`;

  const response = await fetch(url);
  const data = await response.json();

  sugestoesBox.innerHTML = "";

  if (data.length === 0) {
    sugestoesBox.style.display = "none";
    return;
  }

  data.forEach(local => {

    const item = document.createElement("div");
    item.style.padding = "8px";
    item.style.cursor = "pointer";
    item.style.borderBottom = "1px solid #eee";
    item.innerText = local.display_name;

    item.addEventListener("click", function () {

      const lat = parseFloat(local.lat);
      const lng = parseFloat(local.lon);

      map.setView([lat, lng], 16);

      if (marcadorBusca) {
        map.removeLayer(marcadorBusca);
      }

      marcadorBusca = L.marker([lat, lng])
        .addTo(map)
        .bindPopup(local.display_name)
        .openPopup();

      searchInput.value = local.display_name;
      sugestoesBox.style.display = "none";
    });

    sugestoesBox.appendChild(item);
  });

  sugestoesBox.style.display = "block";
});

// Fecha sugestões ao clicar fora
document.addEventListener("click", function (e) {
  if (!searchInput.contains(e.target) && !sugestoesBox.contains(e.target)) {
    sugestoesBox.style.display = "none";
  }
});