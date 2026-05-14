const body = document.body;
const tabButtons = Array.from(document.querySelectorAll("[data-tab-target]"));
const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
const tabShortcuts = Array.from(document.querySelectorAll("[data-tab-shortcut]"));
const miniMapNodes = Array.from(document.querySelectorAll("[data-mini-map]"));
const discussionToggles = Array.from(document.querySelectorAll("[data-discussion-toggle]"));
const miniMaps = [];
let mapsInitialized = false;

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
  }, { threshold: 0.12 });

  revealNodes.forEach((node) => observer.observe(node));
}

function refreshMiniMaps() {
  miniMaps.forEach((map) => {
    window.setTimeout(() => {
      map.invalidateSize();
    }, 120);
  });
}

function initializeMiniMaps() {
  if (mapsInitialized || !miniMapNodes.length || typeof L === "undefined") {
    return;
  }

  miniMapNodes.forEach((node) => {
    const lat = Number.parseFloat(node.dataset.lat || "");
    const lng = Number.parseFloat(node.dataset.lng || "");

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return;
    }

    const miniMap = L.map(node, {
      zoomControl: false,
      attributionControl: false,
      dragging: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      boxZoom: false,
      keyboard: false,
      touchZoom: false,
    }).setView([lat, lng], 15);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
    }).addTo(miniMap);

    L.circleMarker([lat, lng], {
      radius: 8,
      fillColor: "#c94d46",
      color: "#ffffff",
      weight: 2,
      fillOpacity: 0.94,
    }).addTo(miniMap).bindPopup(`<strong>${node.dataset.title}</strong><br>${node.dataset.address}`);

    miniMaps.push(miniMap);
  });

  mapsInitialized = true;
  refreshMiniMaps();
}

function activateTab(tabName) {
  tabButtons.forEach((button) => {
    const isActive = button.dataset.tabTarget === tabName;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  tabPanels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.tabPanel === tabName);
  });

  if (body) {
    body.dataset.activeTab = tabName;
  }

  if (tabName === "feed") {
    initializeMiniMaps();
    refreshMiniMaps();
  }
}

function setDiscussionState(toggle, expanded) {
  const targetId = toggle.dataset.targetId;
  if (!targetId) {
    return;
  }

  const panel = document.getElementById(targetId);
  const label = toggle.querySelector(".discussion-toggle-label");
  if (!panel || !label) {
    return;
  }

  toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
  panel.hidden = !expanded;
  label.textContent = expanded ? "Fechar comentarios" : "Abrir comentarios";
}

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activateTab(button.dataset.tabTarget);
  });
});

tabShortcuts.forEach((button) => {
  button.addEventListener("click", () => {
    const targetTab = button.dataset.tabShortcut;
    if (targetTab) {
      activateTab(targetTab);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });
});

discussionToggles.forEach((toggle) => {
  setDiscussionState(toggle, false);
  toggle.addEventListener("click", () => {
    const isExpanded = toggle.getAttribute("aria-expanded") === "true";
    setDiscussionState(toggle, !isExpanded);
  });
});

document.addEventListener("DOMContentLoaded", () => {
  setupRevealAnimations();
  activateTab(body?.dataset.activeTab || "feed");
});
