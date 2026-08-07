const fileInput = document.getElementById("foto_perfil");
const previewImage = document.querySelector("[data-avatar-image]");
const previewFallback = document.querySelector("[data-avatar-fallback]");
const uploadLabel = document.querySelector("[data-upload-label]");

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
  }, { threshold: 0.16 });

  revealNodes.forEach((node) => observer.observe(node));
}

if (fileInput && previewImage && previewFallback) {
  fileInput.addEventListener("change", (event) => {
    const [file] = event.target.files || [];

    if (!file) {
      previewImage.hidden = true;
      previewImage.removeAttribute("src");
      previewFallback.hidden = false;
      if (uploadLabel) {
        uploadLabel.textContent = "Adicionar foto de perfil";
      }
      return;
    }

    const reader = new FileReader();
    reader.addEventListener("load", () => {
      previewImage.src = reader.result;
      previewImage.hidden = false;
      previewFallback.hidden = true;
      if (uploadLabel) {
        uploadLabel.textContent = `Foto selecionada: ${file.name}`;
      }
    });
    reader.readAsDataURL(file);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupRevealAnimations();
});
