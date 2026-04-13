const form = document.getElementById("form");
const lista = document.getElementById("lista");

let chamados = JSON.parse(localStorage.getItem("chamados")) || [];

function salvar() {
  localStorage.setItem("chamados", JSON.stringify(chamados));
}

function classeStatus(status) {
  if (status === "Problema") return "problema";
  if (status === "Pendente") return "pendente";
  if (status === "Resolvido") return "resolvido";
  return "";
}

function render() {

  const usuarioLogado = JSON.parse(localStorage.getItem("usuarioLogado"));

  lista.innerHTML = "";

  chamados
    .filter(c => c.userId === usuarioLogado?.id)
    .forEach((c, index) => {

      const div = document.createElement("div");
      div.className = "card-chamado";

      div.innerHTML = `
        <strong>${c.categoria}</strong><br>
        ${c.descricao}<br>
        📍 ${c.local}<br>

        ${c.imagem ? `<img src="${c.imagem}" style="max-width:100%;margin-top:8px;border-radius:8px;">` : ""}

        <br>

        <span class="status ${classeStatus(c.status)}">
          ${c.status}
        </span>

        <br>
        <button onclick="editar(${chamados.indexOf(c)})">
          Atualizar Status
        </button>
      `;

      lista.appendChild(div);
    });
}

form.addEventListener("submit", function (e) {
  e.preventDefault();

  const usuarioLogado = JSON.parse(localStorage.getItem("usuarioLogado"));

  if (!usuarioLogado) {
    alert("Você precisa estar logado.");
    return;
  }

  const nome = document.getElementById("nome").value;
  const email = document.getElementById("email").value;
  const categoria = document.getElementById("categoria").value;
  const descricao = document.getElementById("descricao").value;
  const rua = document.getElementById("rua").value;
  const numero = document.getElementById("numero").value;
  const cidade = document.getElementById("cidade").value;
  const fotoInput = document.getElementById("foto");

  const local = `${rua}, ${numero} - ${cidade}`;

  const arquivo = fotoInput.files[0];

  if (arquivo) {

    const reader = new FileReader();

    reader.onload = function (event) {

      salvarChamado({
        nome,
        email,
        categoria,
        descricao,
        local,
        imagem: event.target.result,
        userId: usuarioLogado.id
      });

    };

    reader.readAsDataURL(arquivo);

  } else {

    salvarChamado({
      nome,
      email,
      categoria,
      descricao,
      local,
      imagem: null,
      userId: usuarioLogado.id
    });

  }
});

function salvarChamado(dados) {

  chamados.push({
    id: Date.now(),
    ...dados,
    status: "Problema"
  });

  salvar();
  render();
  form.reset();
}

function editar(index) {

  const novoStatus = prompt(
    "Digite o novo status:\nProblema / Pendente / Resolvido"
  );

  if (
    novoStatus === "Problema" ||
    novoStatus === "Pendente" ||
    novoStatus === "Resolvido"
  ) {
    chamados[index].status = novoStatus;
    salvar();
    render();
  } else {
    alert("Status inválido!");
  }
}

render();

 function buscarCEP() {
            let cep = document.getElementById("cep").value.replace(/\D/g, "");

            if (cep.length !== 8) {
                alert("Digite um CEP válido");
                return;
            }

            fetch(`https://viacep.com.br/ws/${cep}/json/`)
                .then(response => response.json())
                .then(dados => {
                    document.getElementById("rua").value = dados.logradouro;
                    document.getElementById("bairro").value = dados.bairro;
                    document.getElementById("cidade").value = dados.localidade;
                });
        }


        function voltar() {
            window.location.href = "index 1.html";
        }

        const inputFoto = document.getElementById("foto");
const nomeArquivo = document.getElementById("nomeArquivo");

if (inputFoto) {
  inputFoto.addEventListener("change", function() {
    if (this.files.length > 0) {
      nomeArquivo.textContent = "Arquivo selecionado: " + this.files[0].name;
    } else {
      nomeArquivo.textContent = "";
    }
  });
}