function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

const mapElement = document.getElementById("map");
const searchInput = document.querySelector(".search");
const sugestoesBox = document.getElementById("sugestoes");

if (mapElement && typeof L !== "undefined") {
  const mapDataElement = document.getElementById("map-data");
  const chamados = mapDataElement ? JSON.parse(mapDataElement.textContent || "[]") : [];
  const fallbackCenter = [-23.5505, -46.6333];
  const map = L.map("map", { zoomControl: false }).setView(fallbackCenter, chamados.length ? 13 : 11);

  L.control.zoom({ position: "topright" }).addTo(map);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  let marcadorBusca = null;

  const marcadores = chamados
    .filter((chamado) => typeof chamado.latitude === "number" && typeof chamado.longitude === "number")
    .map((chamado) => {
      const comentarios = chamado.comentarios.length
        ? `<ul>${chamado.comentarios
            .map((comentario) => `<li>${escapeHtml(comentario)}</li>`)
            .join("")}</ul>`
        : "<p>Sem comentarios.</p>";

      const popupHTML = `
        <strong>${escapeHtml(chamado.categoria)}</strong><br>
        ${escapeHtml(chamado.descricao)}<br>
        <strong>Endereco:</strong> ${escapeHtml(chamado.endereco)}<br>
        <strong>Status:</strong> ${escapeHtml(chamado.status)}<br><br>
        <strong>Comentarios</strong>
        ${comentarios}
      `;

      const marcador = L.circleMarker([chamado.latitude, chamado.longitude], {
        radius: 8,
        fillColor: chamado.status_color,
        color: "#000",
        weight: 1,
        fillOpacity: 0.8,
      })
        .addTo(map)
        .bindPopup(popupHTML);

      return {
        ...chamado,
        marcador,
        searchText: `${chamado.categoria} ${chamado.endereco} ${chamado.descricao}`.toLowerCase(),
      };
    });

  if (marcadores.length) {
    const bounds = L.latLngBounds(marcadores.map((item) => [item.latitude, item.longitude]));
    map.fitBounds(bounds.pad(0.2));
  }

  function limparSugestoes() {
    if (!sugestoesBox) {
      return;
    }
    sugestoesBox.innerHTML = "";
    sugestoesBox.style.display = "none";
  }

  function adicionarSugestao(label, onClick) {
    if (!sugestoesBox) {
      return;
    }

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

      debounceId = window.setTimeout(async () => {
        limparSugestoes();

        marcadores
          .filter((item) => item.searchText.includes(termo))
          .slice(0, 5)
          .forEach((item) => {
            adicionarSugestao(`${item.categoria} - ${item.endereco}`, () => {
              map.setView([item.latitude, item.longitude], 16);
              item.marcador.openPopup();
              searchInput.value = `${item.categoria} - ${item.endereco}`;
              limparSugestoes();
            });
          });

        try {
          const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(searchInput.value.trim())}`
          );
          const data = await response.json();

          data.forEach((local) => {
            adicionarSugestao(local.display_name, () => {
              const lat = parseFloat(local.lat);
              const lng = parseFloat(local.lon);
              map.setView([lat, lng], 17);

              if (marcadorBusca) {
                map.removeLayer(marcadorBusca);
              }

              marcadorBusca = L.marker([lat, lng]).addTo(map).bindPopup(local.display_name).openPopup();
              searchInput.value = local.display_name;
              limparSugestoes();
            });
          });
        } catch (_error) {
        }

        if (sugestoesBox.children.length) {
          sugestoesBox.style.display = "block";
        }
      }, 300);
    });

    document.addEventListener("click", (event) => {
      if (!sugestoesBox.contains(event.target) && event.target !== searchInput) {
        limparSugestoes();
      }
    });
  }
}

function irParaSobre() {
  const footer = document.querySelector(".footer");
  if (footer) {
    footer.scrollIntoView({ behavior: "smooth" });
  }
}

const ano = document.getElementById("ano");
if (ano) {
  ano.textContent = new Date().getFullYear();
}