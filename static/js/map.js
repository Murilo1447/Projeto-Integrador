const mapElement = document.getElementById("map");

if (mapElement) {
  const chamados = JSON.parse(document.getElementById("map-data").textContent);
  const searchInput = document.getElementById("map-search");

  const fallbackCenter = [-23.55052, -46.633308];
  const initialCenter = chamados.length ? [chamados[0].latitude, chamados[0].longitude] : fallbackCenter;
  const map = L.map("map", { zoomControl: false }).setView(initialCenter, chamados.length ? 13 : 11);

  L.control.zoom({ position: "topright" }).addTo(map);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  const markerData = chamados.map((chamado) => {
    const comentarios = chamado.comentarios.length
      ? `<ul>${chamado.comentarios.map((comentario) => `<li>${comentario}</li>`).join("")}</ul>`
      : "<p>Sem comentarios ate o momento.</p>";

    const marker = L.circleMarker([chamado.latitude, chamado.longitude], {
      radius: 9,
      fillColor: chamado.status_color,
      color: "#102022",
      weight: 1,
      fillOpacity: 0.88,
    }).addTo(map);

    marker.bindPopup(`
      <strong>${chamado.categoria}</strong><br>
      ${chamado.descricao}<br><br>
      <strong>Endereco:</strong> ${chamado.endereco}<br>
      <strong>Status:</strong> ${chamado.status}<br><br>
      <strong>Comentarios</strong>
      ${comentarios}
    `);

    return {
      ...chamado,
      marker,
      searchText: `${chamado.categoria} ${chamado.endereco} ${chamado.descricao}`.toLowerCase(),
    };
  });

  if (markerData.length) {
    const bounds = L.latLngBounds(markerData.map(({ latitude, longitude }) => [latitude, longitude]));
    map.fitBounds(bounds.pad(0.2));
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const term = searchInput.value.trim().toLowerCase();

      if (!term) {
        if (markerData.length) {
          const bounds = L.latLngBounds(markerData.map(({ latitude, longitude }) => [latitude, longitude]));
          map.fitBounds(bounds.pad(0.2));
        }
        return;
      }

      const match = markerData.find((item) => item.searchText.includes(term));
      if (match) {
        map.setView([match.latitude, match.longitude], 16);
        match.marker.openPopup();
      }
    });
  }
}
