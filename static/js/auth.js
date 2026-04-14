const fileInput = document.getElementById("foto_perfil");
const previewImage = document.querySelector("[data-avatar-image]");
const previewFallback = document.querySelector("[data-avatar-fallback]");

if (fileInput && previewImage && previewFallback) {
  fileInput.addEventListener("change", (event) => {
    const [file] = event.target.files || [];
    if (!file) {
      previewImage.hidden = true;
      previewImage.removeAttribute("src");
      previewFallback.hidden = false;
      return;
    }

    const reader = new FileReader();
    reader.addEventListener("load", () => {
      previewImage.src = reader.result;
      previewImage.hidden = false;
      previewFallback.hidden = true;
    });
    reader.readAsDataURL(file);
  });
}
