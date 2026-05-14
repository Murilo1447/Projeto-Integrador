function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setupRevealAnimations() {
  const revealNodes = document.querySelectorAll("[data-reveal]");
  if (!revealNodes.length) {
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.18 });

  revealNodes.forEach((node) => observer.observe(node));
}

function setupFooterYear() {
  const ano = document.getElementById("ano");
  if (ano) {
    ano.textContent = new Date().getFullYear();
  }
}

function setupDraggablePanels() {
  const panels = Array.from(document.querySelectorAll('[data-draggable="true"], .floating-panel'));
  if (!panels.length) {
    return;
  }

  let zIndexSeed = 2500;

  panels.forEach((panel) => {
    const handle = panel.querySelector("[data-drag-handle]");
    if (!handle) {
      return;
    }

    function bringToFront() {
      zIndexSeed += 1;
      panel.style.zIndex = String(zIndexSeed);
    }

    let dragging = false;
    let pointerId = null;
    let startX = 0;
    let startY = 0;
    let startLeft = 0;
    let startTop = 0;

    function normalizePosition() {
      const rect = panel.getBoundingClientRect();
      panel.style.left = `${rect.left}px`;
      panel.style.top = `${rect.top}px`;
      panel.style.right = "auto";
      panel.style.bottom = "auto";
      panel.style.transform = "none";
    }

    function onPointerMove(event) {
      if (!dragging || event.pointerId !== pointerId) {
        return;
      }

      const nextLeft = startLeft + (event.clientX - startX);
      const nextTop = startTop + (event.clientY - startY);
      const maxLeft = Math.max(16, window.innerWidth - panel.offsetWidth - 16);
      const maxTop = Math.max(16, window.innerHeight - panel.offsetHeight - 16);

      panel.style.left = `${Math.min(Math.max(16, nextLeft), maxLeft)}px`;
      panel.style.top = `${Math.min(Math.max(16, nextTop), maxTop)}px`;
    }

    function onPointerUp(event) {
      if (event.pointerId !== pointerId) {
        return;
      }

      dragging = false;
      pointerId = null;
      handle.classList.remove("is-dragging");
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", onPointerUp);
    }

    handle.addEventListener("pointerdown", (event) => {
      if (window.innerWidth <= 760) {
        return;
      }

      event.preventDefault();
      bringToFront();
      normalizePosition();
      dragging = true;
      pointerId = event.pointerId;
      startX = event.clientX;
      startY = event.clientY;
      startLeft = Number.parseFloat(panel.style.left || "0");
      startTop = Number.parseFloat(panel.style.top || "0");
      handle.classList.add("is-dragging");

      document.addEventListener("pointermove", onPointerMove);
      document.addEventListener("pointerup", onPointerUp);
    });

    panel.addEventListener("pointerdown", bringToFront);
  });
}

function setupMinimizablePanels() {
  const toggles = Array.from(document.querySelectorAll("[data-panel-toggle]"));
  if (!toggles.length) {
    return;
  }

  toggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const panel = toggle.closest(".floating-panel");
      if (!panel) {
        return;
      }

      const minimized = panel.classList.toggle("is-minimized");
      toggle.textContent = minimized ? "Restaurar" : "Minimizar";
      toggle.setAttribute("aria-expanded", minimized ? "false" : "true");
    });
  });
}

function setupMap() {
  const mapElement = document.getElementById("map");
  if (!mapElement || typeof L === "undefined") {
    return;
  }

  const pageBody = document.body;
  const panelMode = pageBody?.dataset.panelMode || "overlay";
  const mapDataElement = document.getElementById("map-data");
  const chamados = mapDataElement ? JSON.parse(mapDataElement.textContent || "[]") : [];
  const fallbackCenter = [-23.5505, -46.6333];
  const searchInput = document.querySelector(".search");
  const sugestoesBox = document.getElementById("sugestoes");
  const overlay = document.getElementById("map-overlay");
  const toggleButton = document.getElementById("toggle-map");
  const openCreatePanelButton = document.getElementById("open-create-panel");
  const openCreatePanelInsideButton = document.getElementById("open-create-panel-inside");
  const resetMapViewButton = document.getElementById("reset-map-view");
  const mapWrapper = document.querySelector(".map-wrapper");
  const mapSection = document.getElementById("mapa");
  const panelBackdrop = document.getElementById("floating-panel-backdrop");
  const detailPanel = document.getElementById("map-post-panel");
  const createPanel = document.getElementById("create-post-panel");
  const closePanelButtons = document.querySelectorAll("[data-close-floating-panel]");
  const previewTriggers = document.querySelectorAll("[data-map-post-trigger]");
  const feedUrl = pageBody?.dataset.feedUrl || "#";
  const createUrl = pageBody?.dataset.createUrl || "#";
  let searchMarker = null;
  let activePanel = null;
  let defaultBounds = null;

  const map = L.map("map", {
    zoomControl: false,
    scrollWheelZoom: false,
  }).setView(fallbackCenter, chamados.length ? 13 : 11);

  L.control.zoom({ position: "topright" }).addTo(map);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  function unlockMap() {
    map.scrollWheelZoom.enable();
    overlay?.classList.add("hidden");
  }

  function lockMap() {
    map.scrollWheelZoom.disable();
    overlay?.classList.remove("hidden");
  }

  function refreshMapSize() {
    window.setTimeout(() => {
      map.invalidateSize({ animate: true });
    }, 320);
  }

  function setMapExpanded(expanded, scrollIntoView = false) {
    if (!mapSection) {
      return;
    }

    mapElement.classList.toggle("expanded", expanded);
    mapSection.classList.toggle("map-live-mode", expanded);

    if (toggleButton) {
      toggleButton.textContent = expanded ? "Reduzir mapa" : "Expandir mapa";
    }

    refreshMapSize();

    if (scrollIntoView) {
      mapSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function updateBackdrop(show) {
    if (!panelBackdrop) {
      return;
    }
    panelBackdrop.hidden = !(show && panelMode === "overlay");
  }

  function hidePanel(panel) {
    if (!panel) {
      return;
    }
    const toggle = panel.querySelector("[data-panel-toggle]");
    panel.classList.remove("is-minimized");
    if (toggle) {
      toggle.textContent = "Minimizar";
      toggle.setAttribute("aria-expanded", "true");
    }
    panel.hidden = true;
    panel.setAttribute("aria-hidden", "true");
  }

  function showPanel(panel) {
    if (!panel) {
      return;
    }
    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
  }

  function closeFloatingPanels() {
    activePanel = null;
    hidePanel(detailPanel);
    hidePanel(createPanel);
    updateBackdrop(false);
  }

  function openFloatingPanel(panel) {
    if (!panel) {
      return;
    }

    [detailPanel, createPanel].forEach((candidate) => {
      if (candidate && candidate !== panel) {
        hidePanel(candidate);
      }
    });

    activePanel = panel;
    panel.style.zIndex = "2600";
    showPanel(panel);
    updateBackdrop(true);
  }

  function renderComments(comments) {
    if (!comments?.length) {
      return '<div class="panel-comment-empty">Sem comentarios ainda para esta denuncia.</div>';
    }

    return comments
      .map((comment) => `
        <article class="panel-comment">
          <div class="panel-comment-head">
            <strong>${escapeHtml(comment.autor)}</strong>
            <span>${escapeHtml(comment.tempo_relativo)}</span>
          </div>
          <p>${escapeHtml(comment.texto)}</p>
        </article>
      `)
      .join("");
  }

  function openDetailPanel(chamado) {
    if (!detailPanel || !chamado) {
      return;
    }

    const title = detailPanel.querySelector("#map-post-title");
    const status = detailPanel.querySelector("#map-post-status");
    const author = detailPanel.querySelector("#map-post-author");
    const meta = detailPanel.querySelector("#map-post-meta");
    const description = detailPanel.querySelector("#map-post-description");
    const address = detailPanel.querySelector("#map-post-address");
    const tags = detailPanel.querySelector("#map-post-tags");
    const comments = detailPanel.querySelector("#map-post-comments");
    const feedLink = detailPanel.querySelector("#map-post-feed-link");

    if (title) {
      title.textContent = chamado.categoria;
    }
    if (status) {
      status.textContent = chamado.status;
      status.className = `status-badge ${chamado.status_css || ""}`;
    }
    if (author) {
      author.textContent = chamado.autor;
    }
    if (meta) {
      meta.textContent = chamado.tempo_relativo;
    }
    if (description) {
      description.textContent = chamado.descricao;
    }
    if (address) {
      address.textContent = chamado.endereco;
    }
    if (tags) {
      tags.innerHTML = `
        <span class="panel-tag">${escapeHtml(chamado.upvotes_label)}</span>
        <span class="panel-tag">${escapeHtml(chamado.comentarios_label)}</span>
      `;
    }
    if (comments) {
      comments.innerHTML = renderComments(chamado.comentarios);
    }
    if (feedLink) {
      feedLink.href = feedUrl;
    }

    openFloatingPanel(detailPanel);
  }

  function resetMapView() {
    if (defaultBounds) {
      map.fitBounds(defaultBounds.pad(0.2));
      return;
    }
    map.setView(fallbackCenter, chamados.length ? 13 : 11);
  }

  map.on("click", unlockMap);
  lockMap();

  if (mapWrapper) {
    document.addEventListener("click", (event) => {
      if (!mapWrapper.contains(event.target)) {
        lockMap();
      }
    });
  }

  if (toggleButton) {
    toggleButton.addEventListener("click", () => {
      setMapExpanded(!mapSection?.classList.contains("map-live-mode"));
    });
  }

  if (openCreatePanelButton) {
    openCreatePanelButton.addEventListener("click", () => {
      openFloatingPanel(createPanel);
    });
  }

  if (openCreatePanelInsideButton) {
    openCreatePanelInsideButton.addEventListener("click", () => {
      window.location.href = createUrl;
    });
  }

  if (resetMapViewButton) {
    resetMapViewButton.addEventListener("click", resetMapView);
  }

  if (panelBackdrop) {
    panelBackdrop.addEventListener("click", closeFloatingPanels);
  }

  closePanelButtons.forEach((button) => {
    button.addEventListener("click", closeFloatingPanels);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && activePanel) {
      closeFloatingPanels();
    }
  });

  const markers = chamados
    .filter((chamado) => Number.isFinite(chamado.latitude) && Number.isFinite(chamado.longitude))
    .map((chamado) => {
      const marker = L.circleMarker([chamado.latitude, chamado.longitude], {
        radius: 8,
        fillColor: chamado.status_color,
        color: "#ffffff",
        weight: 2,
        fillOpacity: 0.92,
      }).addTo(map);

      marker.on("click", () => {
        openDetailPanel(chamado);
      });

      return {
        ...chamado,
        marker,
        searchText: `${chamado.categoria} ${chamado.endereco} ${chamado.descricao}`.toLowerCase(),
      };
    });

  if (markers.length) {
    defaultBounds = L.latLngBounds(markers.map((item) => [item.latitude, item.longitude]));
    map.fitBounds(defaultBounds.pad(0.2));
  }

  function clearSuggestions() {
    if (!sugestoesBox) {
      return;
    }
    sugestoesBox.innerHTML = "";
    sugestoesBox.style.display = "none";
  }

  function appendSuggestion(label, onClick) {
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
      const query = searchInput.value.trim().toLowerCase();
      window.clearTimeout(debounceId);

      if (query.length < 3) {
        clearSuggestions();
        return;
      }

      debounceId = window.setTimeout(async () => {
        clearSuggestions();

        markers
          .filter((marker) => marker.searchText.includes(query))
          .slice(0, 5)
          .forEach((marker) => {
            appendSuggestion(`${marker.categoria} - ${marker.endereco}`, () => {
              map.setView([marker.latitude, marker.longitude], 16);
              openDetailPanel(marker);
              searchInput.value = `${marker.categoria} - ${marker.endereco}`;
              clearSuggestions();
            });
          });

        try {
          const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(searchInput.value)}`
          );
          const places = await response.json();

          places.forEach((place) => {
            appendSuggestion(place.display_name, () => {
              const lat = Number.parseFloat(place.lat);
              const lng = Number.parseFloat(place.lon);
              map.setView([lat, lng], 17);

              if (searchMarker) {
                map.removeLayer(searchMarker);
              }

              searchMarker = L.marker([lat, lng]).addTo(map).bindPopup(place.display_name).openPopup();
              searchInput.value = place.display_name;
              clearSuggestions();
            });
          });
        } catch (_error) {
        }

        if (sugestoesBox.children.length) {
          sugestoesBox.style.display = "block";
        }
      }, 260);
    });

    document.addEventListener("click", (event) => {
      if (!sugestoesBox.contains(event.target) && event.target !== searchInput) {
        clearSuggestions();
      }
    });
  }

  previewTriggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const chamado = chamados.find((item) => String(item.id) === String(trigger.dataset.postId));
      if (!chamado) {
        return;
      }

      if (Number.isFinite(chamado.latitude) && Number.isFinite(chamado.longitude)) {
        map.setView([chamado.latitude, chamado.longitude], 16);
      }

      openDetailPanel(chamado);
    });
  });

  refreshMapSize();
}

document.addEventListener("DOMContentLoaded", () => {
  setupRevealAnimations();
  setupFooterYear();
  setupDraggablePanels();
  setupMinimizablePanels();
  setupMap();
});
