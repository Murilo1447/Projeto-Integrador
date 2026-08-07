// ==========================
// UTILIDADES
// ==========================

function validarCPF(telefone) {
  telefone = telefone.replace(/\D/g, "");
  return telefone.length === 11;
}

// ==========================
// CADASTRO
// ==========================

const formCadastro = document.getElementById("formCadastro");

if (formCadastro) {
  formCadastro.addEventListener("submit", function (e) {
    e.preventDefault();

    const nome = document.getElementById("nome").value;
    const telefone = document.getElementById("telefone").value;
    const email = document.getElementById("email").value;
    const senha = document.getElementById("senha").value;

    if (!validarCPF(cpf)) {
      alert("CPF inválido!");
      return;
    }

    let usuarios = JSON.parse(localStorage.getItem("usuarios")) || [];

    if (usuarios.find(u => u.email === email)) {
      alert("Email já cadastrado!");
      return;
    }

    const novoUsuario = {
      id: Date.now(),
      nome,
      telefone,
      email,
      senha
    };
                         
    usuarios.push(novoUsuario);
    localStorage.setItem("usuarios", JSON.stringify(usuarios));

    alert("Cadastro realizado com sucesso!");
    window.location.href = "login.html";
  });
}

// ==========================
// LOGIN
// ==========================

const formLogin = document.getElementById("formLogin");

if (formLogin) {
  formLogin.addEventListener("submit", function (e) {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value;
    const senha = document.getElementById("loginSenha").value;

    let usuarios = JSON.parse(localStorage.getItem("usuarios")) || [];

    const usuario = usuarios.find(
      u => u.email === email && u.senha === senha
    );

    if (!usuario) {
      alert("Email ou senha incorretos!");
      return;
    }

    localStorage.setItem("usuarioLogado", JSON.stringify(usuario));

    alert("Login realizado com sucesso!");
    window.location.href = "index.html";
  });
}