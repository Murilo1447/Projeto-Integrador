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

document.addEventListener("DOMContentLoaded", function () {
    const inputFoto = document.getElementById("foto_perfil");
    const previewImg = document.querySelector("[data-avatar-image]");
    const fallbackSvg = document.querySelector("[data-avatar-fallback]");

    if (inputFoto) {
        inputFoto.addEventListener("change", function () {
            const arquivo = this.files[0];

            if (arquivo) {
                const leitor = new FileReader();

                leitor.onload = function (e) {
                    // Mostra a imagem e esconde o SVG
                    previewImg.src = e.target.result;
                    previewImg.hidden = false;
                    if (fallbackSvg) fallbackSvg.style.display = "none";
                };

                leitor.readAsDataURL(arquivo);
            }
        });
    }
});
