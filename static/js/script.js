function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

document.addEventListener("DOMContentLoaded", function () {

  const mapElement = document.getElementById("map");
  const searchInput = document.querySelector(".search");
  const sugestoesBox = document.getElementById("sugestoes");

  if (mapElement && typeof L !== "undefined") {

    const mapDataElement = document.getElementById("map-data");
    const chamados = mapDataElement
      ? JSON.parse(mapDataElement.textContent || "[]")
      : [];

    /* =========================
        STATUS SUPERIOR
    ========================== */

    const totalProblemas = chamados.filter(c =>
      c.status?.toLowerCase().includes("problema")
    ).length;

    const totalPendentes = chamados.filter(c =>
      c.status?.toLowerCase().includes("andamento") ||
      c.status?.toLowerCase().includes("pendente")
    ).length;

    const totalResolvidos = chamados.filter(c =>
      c.status?.toLowerCase().includes("resolvido")
    ).length;

    const elProblemas = document.getElementById("total-problemas");
    const elPendentes = document.getElementById("total-pendentes");
    const elResolvidos = document.getElementById("total-resolvidos");

    if (elProblemas) elProblemas.textContent = totalProblemas;
    if (elPendentes) elPendentes.textContent = totalPendentes;
    if (elResolvidos) elResolvidos.textContent = totalResolvidos;

    /* =========================
              MAPA
    ========================== */

    const fallbackCenter = [-23.5505, -46.6333];

    const map = L.map("map", {
      zoomControl: false,
      scrollWheelZoom: false
    }).setView(fallbackCenter, chamados.length ? 13 : 11);

    L.control.zoom({ position: "topright" }).addTo(map);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);

    const overlay = document.getElementById("map-overlay");

    const mapWrapper = document.querySelector(".map-wrapper");

function ativarMapa() {
  map.scrollWheelZoom.enable();
  if (overlay) overlay.classList.add("hidden");
}

function travarMapa() {
  map.scrollWheelZoom.disable();
  if (overlay) overlay.classList.remove("hidden");
}

// Começa travado
travarMapa();

// Clique dentro do mapa ativa
map.on("click", function () {
  ativarMapa();
});

// Clique fora do mapa trava novamente
document.addEventListener("click", function (event) {
  if (!mapWrapper.contains(event.target)) {
    travarMapa();
  }


  /* =========================
    BOTÃO EXPANDIR/REDUZIR
========================== */
const btnToggleMap = document.getElementById("toggle-map");

if (btnToggleMap && mapElement) {
  btnToggleMap.addEventListener("click", function () {
    // Alterna a classe 'expanded' no elemento do mapa
    mapElement.classList.toggle("expanded");

    // Atualiza o texto do botão
    if (mapElement.classList.contains("expanded")) {
      btnToggleMap.textContent = "Reduzir mapa";
    } else {
      btnToggleMap.textContent = "Expandir mapa";
    }

    // Força o Leaflet a recalcular o tamanho do container após a transição
    setTimeout(() => {
      map.invalidateSize({ animate: true });
    }, 400); // 400ms coincide com a transição CSS (0.4s)
  });
}
});
    let marcadorBusca = null;

    const marcadores = chamados
      .filter(c => typeof c.latitude === "number" && typeof c.longitude === "number")
      .map((chamado) => {

        const comentarios = chamado.comentarios?.length
          ? `<ul>${chamado.comentarios
              .map(c => `<li>${escapeHtml(c)}</li>`)
              .join("")}</ul>`
          : "<p>Sem comentários.</p>";

        const popupHTML = `
          <strong>${escapeHtml(chamado.categoria)}</strong><br>
          ${escapeHtml(chamado.descricao)}<br>
          <strong>Endereço:</strong> ${escapeHtml(chamado.endereco)}<br>
          <strong>Status:</strong> ${escapeHtml(chamado.status)}<br><br>
          <strong>Comentários</strong>
          ${comentarios}
        `;

        const marcador = L.circleMarker(
          [chamado.latitude, chamado.longitude],
          {
            radius: 8,
            fillColor: chamado.status_color,
            color: "#000",
            weight: 1,
            fillOpacity: 0.85,
          }
        )
          .addTo(map)
          .bindPopup(popupHTML);

        return {
          ...chamado,
          marcador,
          searchText: `${chamado.categoria} ${chamado.endereco} ${chamado.descricao}`.toLowerCase(),
        };
      });

    if (marcadores.length) {
      const bounds = L.latLngBounds(
        marcadores.map(m => [m.latitude, m.longitude])
      );
      map.fitBounds(bounds.pad(0.2));
    }

    /* =========================
                BUSCA
    ========================== */

    function limparSugestoes() {
      if (!sugestoesBox) return;
      sugestoesBox.innerHTML = "";
      sugestoesBox.style.display = "none";
    }

    function adicionarSugestao(label, onClick) {
      if (!sugestoesBox) return;
      const item = document.createElement("div");
      item.textContent = label;
      item.addEventListener("click", onClick);
      sugestoesBox.appendChild(item);
    }

    if (searchInput && sugestoesBox) {
      let debounceId = null;

      searchInput.addEventListener("input", () => {
        const termo = searchInput.value.trim().toLowerCase();
        clearTimeout(debounceId);

        if (termo.length < 3) {
          limparSugestoes();
          return;
        }

        debounceId = setTimeout(async () => {
          limparSugestoes();

          marcadores
            .filter(m => m.searchText.includes(termo))
            .slice(0, 5)
            .forEach((m) => {
              adicionarSugestao(`${m.categoria} - ${m.endereco}`, () => {
                map.setView([m.latitude, m.longitude], 16);
                m.marcador.openPopup();
                searchInput.value = `${m.categoria} - ${m.endereco}`;
                limparSugestoes();
              });
            });

          try {
            const response = await fetch(
              `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(searchInput.value)}`
            );
            const data = await response.json();

            data.forEach(local => {
              adicionarSugestao(local.display_name, () => {
                const lat = parseFloat(local.lat);
                const lng = parseFloat(local.lon);
                map.setView([lat, lng], 17);

                if (marcadorBusca) {
                  map.removeLayer(marcadorBusca);
                }

                marcadorBusca = L.marker([lat, lng])
                  .addTo(map)
                  .bindPopup(local.display_name)
                  .openPopup();

                searchInput.value = local.display_name;
                limparSugestoes();
              });
            });
          } catch (e) {}

          if (sugestoesBox.children.length) {
            sugestoesBox.style.display = "block";
          }

        }, 300);
      });

      document.addEventListener("click", (event) => {
        if (!sugestoesBox.contains(event.target) &&
            event.target !== searchInput) {
          limparSugestoes();
        }
      });
    }
  }

  /* =========================
            FOOTER
  ========================== */

  const ano = document.getElementById("ano");
  if (ano) {
    ano.textContent = new Date().getFullYear();
  }

});

function irParaSobre() {
  const footer = document.getElementById("rodape");
  if (footer) {
    footer.scrollIntoView({ behavior: "smooth" });
  }
}

const fileInput = document.getElementById('foto_perfil');
const labelFile = document.querySelector('label[for="foto_perfil"]');

if (fileInput) {
    fileInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            // Muda o texto do "botão" para o nome do arquivo selecionado
            labelFile.textContent = "Foto selecionada: " + this.files[0].name;
            labelFile.style.backgroundColor = "#e8f5e9";
            labelFile.style.color = "#2e7d32";
        }
    });
}

document.addEventListener("DOMContentLoaded", function() {
    const modal = document.getElementById("modal-perfil");
    const btnAbrir = document.getElementById("abrir-perfil");
    const spanFechar = document.querySelector(".close-modal");

    if (btnAbrir) {
        btnAbrir.onclick = function() {
            modal.style.display = "block";
        }
    }

    if (spanFechar) {
        spanFechar.onclick = function() {
            modal.style.display = "none";
        }
    }

    // Fecha o modal se clicar fora da caixa branca
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
});