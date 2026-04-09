const form = document.getElementById("form");
const lista = document.getElementById("lista");
 
let chamados = JSON.parse(localStorage.getItem("chamados")) || [];
 
const palavrasProibidas = ["idiota", "burro", "lixo"];
 
function validarCPF(cpf) {
  cpf = cpf.replace(/\D/g, "");
  return cpf.length === 11;
}
 
function textoValido(texto) {
  return !palavrasProibidas.some(p => texto.toLowerCase().includes(p));
}
 
function salvar() {
  localStorage.setItem("chamados", JSON.stringify(chamados));
}
 
// 🎨 Classe do status
function classeStatus(status) {
  if (status === "Problema") return "problema";
  if (status === "Pendente") return "pendente";
  if (status === "Resolvido") return "resolvido";
  return "";
}
 
// 🖥️ Render
function render() {
  lista.innerHTML = "";
 
  chamados.forEach((c, index) => {
    const div = document.createElement("div");
    div.className = "card-chamado";
 
    div.innerHTML = `
      <strong>${c.categoria}</strong><br>
      ${c.descricao}<br>
      📍 ${c.local}<br>
      CPF: ${c.cpf}<br>
 
      <span class="status ${classeStatus(c.status)}">
        ${c.status}
      </span>
 
      <br>
      <button onclick="editar(${index})">Atualizar Status</button>
    `;
 
    lista.appendChild(div);
  });
}
 
// ➕ Criar chamado
form.addEventListener("submit", (e) => {
  e.preventDefault();
 
  const cpf = document.getElementById("cpf").value;
  const nome = document.getElementById("nome").value;
  const email = document.getElementById("email").value;
  const categoria = document.getElementById("categoria").value;
  const descricao = document.getElementById("descricao").value;
  const rua = document.getElementById("rua").value;
  const numero = document.getElementById("numero").value;
  const cidade = document.getElementById("cidade").value;
  
  const local = `${rua}, ${numero} - ${cidade}`;
 
  if (!validarCPF(cpf)) {
    alert("CPF inválido!");
    return;
  }
 
  if (!textoValido(descricao)) {
    alert("Conteúdo inadequado!");
    return;
  }
 
  chamados.push({
    id: Date.now(),
    cpf,
    nome,
    email,
    categoria,
    descricao,
    local,
    status: "Problema" // 🔴 começa como problema
  });
 
  salvar();
  render();
  form.reset();
});
 
// ✏️ Atualizar status
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