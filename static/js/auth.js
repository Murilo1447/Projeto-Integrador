function validarTelefone(telefone) {
  return String(telefone || "").replace(/\D/g, "").length === 11;
}

const routes = window.fixcityRoutes || {
  home: "/",
  login: "/login/",
  cadastro: "/cadastro/",
};

const formCadastro = document.getElementById("formCadastro");
if (formCadastro) {
  formCadastro.addEventListener("submit", (event) => {
    event.preventDefault();

    const nome = document.getElementById("nome").value.trim();
    const telefone = document.getElementById("telefone").value.trim();
    const email = document.getElementById("email").value.trim().toLowerCase();
    const senha = document.getElementById("senha").value;

    if (!validarTelefone(telefone)) {
      alert("Telefone invalido. Use 11 digitos com DDD.");
      return;
    }

    const usuarios = JSON.parse(localStorage.getItem("usuarios") || "[]");
    if (usuarios.find((usuario) => usuario.email === email)) {
      alert("Email ja cadastrado.");
      return;
    }

    const novoUsuario = {
      id: Date.now(),
      nome,
      telefone,
      email,
      senha,
    };

    usuarios.push(novoUsuario);
    localStorage.setItem("usuarios", JSON.stringify(usuarios));
    alert("Cadastro realizado com sucesso.");
    window.location.href = routes.login;
  });
}

const formLogin = document.getElementById("formLogin");
if (formLogin) {
  formLogin.addEventListener("submit", (event) => {
    event.preventDefault();

    const email = document.getElementById("loginEmail").value.trim().toLowerCase();
    const senha = document.getElementById("loginSenha").value;
    const usuarios = JSON.parse(localStorage.getItem("usuarios") || "[]");

    const usuario = usuarios.find((item) => item.email === email && item.senha === senha);
    if (!usuario) {
      alert("Email ou senha incorretos.");
      return;
    }

    localStorage.setItem("usuarioLogado", JSON.stringify(usuario));
    alert("Login realizado com sucesso.");
    window.location.href = routes.home;
  });
}