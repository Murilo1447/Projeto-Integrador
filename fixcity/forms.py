from django import forms

from .models import Chamado, Comentario


PALAVRAS_PROIBIDAS = ("idiota", "burro", "lixo")


def cpf_valido(cpf: str) -> bool:
    numeros = "".join(filter(str.isdigit, cpf))
    if len(numeros) != 11 or len(set(numeros)) == 1:
        return False

    for tamanho in (9, 10):
        soma = sum(int(digito) * peso for digito, peso in zip(numeros[:tamanho], range(tamanho + 1, 1, -1)))
        resto = (soma * 10) % 11
        digito_esperado = 0 if resto == 10 else resto
        if digito_esperado != int(numeros[tamanho]):
            return False

    return True


class ChamadoForm(forms.ModelForm):
    class Meta:
        model = Chamado
        fields = [
            "cpf",
            "nome",
            "email",
            "categoria",
            "cep",
            "rua",
            "bairro",
            "cidade",
            "numero",
            "descricao",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4, "placeholder": "Descreva o problema encontrado"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "cpf": "CPF do solicitante",
            "nome": "Nome (opcional)",
            "email": "E-mail (opcional)",
            "cep": "CEP",
            "rua": "Rua",
            "bairro": "Bairro",
            "cidade": "Cidade",
            "numero": "Numero",
        }
        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
            if field_name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[field_name])

    def clean_cpf(self):
        cpf = "".join(filter(str.isdigit, self.cleaned_data["cpf"]))
        if not cpf_valido(cpf):
            raise forms.ValidationError("Informe um CPF valido.")
        return cpf

    def clean_cep(self):
        cep = "".join(filter(str.isdigit, self.cleaned_data.get("cep", "")))
        if cep and len(cep) != 8:
            raise forms.ValidationError("Informe um CEP com 8 digitos.")
        return cep

    def clean_descricao(self):
        descricao = self.cleaned_data["descricao"].strip()
        descricao_normalizada = descricao.lower()
        if any(palavra in descricao_normalizada for palavra in PALAVRAS_PROIBIDAS):
            raise forms.ValidationError("A descricao contem linguagem inadequada.")
        return descricao


class StatusForm(forms.ModelForm):
    class Meta:
        model = Chamado
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-control status-select"}),
        }


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ["texto"]
        widgets = {
            "texto": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": "form-control",
                    "placeholder": "Adicionar comentario",
                }
            )
        }

    def clean_texto(self):
        texto = self.cleaned_data["texto"].strip()
        if not texto:
            raise forms.ValidationError("Escreva um comentario antes de enviar.")
        return texto
