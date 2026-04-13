// ===============================
// FIXCITY - SCRIPT PRINCIPAL
// ===============================


// ===============================
// MAPA
// ===============================
const map = L.map("map", {
  zoomControl: false
}).setView([-23.5505, -46.6333], 12);

L.control.zoom({
  position: "topright"
}).addTo(map);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap"
}).addTo(map);


// ===============================
// DADOS
// ===============================
let chamados = JSON.parse(localStorage.getItem("chamados")) || [];


// ===============================
// PAINEL DE COMENTÁRIOS
// ===============================
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

function abrirComentarios(index) {
  const chamado = chamados[index];

  let html = "<h4>Comentários</h4>";

  if (chamado.comentarios && chamado.comentarios.length > 0) {
    chamado.comentarios.forEach(c => {
      html += `<p>• ${c}</p>`;
    });
  } else {
    html += "<p>Sem comentários.</p>";
  }

  html += `
    <input type="text" id="novoComentario" placeholder="Adicionar comentário" style="width:100%; margin-top:5px;">
    <button onclick="adicionarComentario(${index})" style="width:100%; margin-top:5px;">Enviar</button>
    <button onclick="fecharComentarios()" style="width:100%; margin-top:5px;">Fechar</button>
  `;

  painel._div.innerHTML = html;
  painel._div.style.display = "block";
}

function fecharComentarios() {
  painel._div.style.display = "none";
}

function adicionarComentario(index) {
  const input = document.getElementById("novoComentario");
  const texto = input.value.trim();
  if (!texto) return;

  if (!chamados[index].comentarios) {
    chamados[index].comentarios = [];
  }

  chamados[index].comentarios.push(texto);
  localStorage.setItem("chamados", JSON.stringify(chamados));

  abrirComentarios(index);
}


// ===============================
// MARCADORES
// ===============================
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

async function buscarCoordenadas(endereco) {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(endereco)}`
    );

    const data = await response.json();

    if (data.length > 0) {
      return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon)
      };
    }

  } catch (error) {
    console.error("Erro ao buscar coordenadas:", error);
  }

  return null;
}

async function renderMapa() {

  for (let i = 0; i < chamados.length; i++) {

    let c = chamados[i];

    let cor =
      c.status === "Resolvido" ? "green" :
      c.status === "Pendente" ? "yellow" :
      "red";

    if (!c.lat || !c.lng) {
      const coord = await buscarCoordenadas(c.local);
      if (coord) {
        c.lat = coord.lat;
        c.lng = coord.lng;
      } else {
        continue;
      }
    }

    const popupHTML = `
      <strong>${c.categoria || ""}</strong><br>
      ${c.nome || ""}<br>
      ${c.descricao || ""}<br>
      ${c.local || ""}<br>
      Status: ${c.status || "Não definido"}<br><br>
      <button onclick="abrirComentarios(${i})">
        Mostrar Comentários
      </button>
    `;

    addMarker(c.lat, c.lng, cor, popupHTML);
  }

  localStorage.setItem("chamados", JSON.stringify(chamados));
}

renderMapa();


// ===============================
// BUSCA SIMPLES (CENTRALIZA MAPA)
// ===============================

const searchInput = document.querySelector(".search");
const sugestoesBox = document.getElementById("sugestoes");

if (searchInput && sugestoesBox) {

  let marcadorBusca = null;
  let debounce;

  function limpar() {
    sugestoesBox.innerHTML = "";
    sugestoesBox.style.display = "none";
  }

  searchInput.addEventListener("input", function () {

    const texto = this.value.trim();
    clearTimeout(debounce);

    if (texto.length < 3) {
      limpar();
      return;
    }

    debounce = setTimeout(async () => {

      try {
        const response = await fetch(
          `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(texto)}`
        );

        const data = await response.json();
        limpar();

        if (!data.length) return;

        data.forEach(local => {

          const item = document.createElement("div");
          item.textContent = local.display_name;
          item.style.padding = "8px";
          item.style.cursor = "pointer";

          item.onclick = function () {

            const lat = parseFloat(local.lat);
            const lng = parseFloat(local.lon);

            // Centraliza mapa
            map.setView([lat, lng], 17);

            // Remove marcador antigo
            if (marcadorBusca) {
              map.removeLayer(marcadorBusca);
            }

            // Adiciona novo marcador
            marcadorBusca = L.marker([lat, lng])
              .addTo(map)
              .bindPopup(local.display_name)
              .openPopup();

            searchInput.value = local.display_name;
            limpar();
          };

          sugestoesBox.appendChild(item);
        });

        sugestoesBox.style.display = "block";

      } catch (error) {
        console.error("Erro na busca:", error);
      }

    }, 400);

  });

  document.addEventListener("click", function (e) {
    if (!sugestoesBox.contains(e.target) && e.target !== searchInput) {
      limpar();
    }
  });
}


// ===============================
// SOBRE
// ===============================
function irParaSobre() {
  const footer = document.querySelector(".footer");
  if (footer) {
    footer.scrollIntoView({ behavior: "smooth" });
  }
}


// ===============================
// ANO AUTOMÁTICO
// ===============================
const ano = document.getElementById("ano");
if (ano) {
  ano.textContent = new Date().getFullYear();
}