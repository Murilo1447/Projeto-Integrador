import json
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_HEADERS = {
    "User-Agent": "FixCity/1.0 (contato-local)",
    "Accept": "application/json",
}


def _fetch_json(url: str):
    request = Request(url, headers=DEFAULT_HEADERS)
    try:
        with urlopen(request, timeout=6) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def buscar_endereco_por_cep(cep: str):
    if not cep:
        return None

    data = _fetch_json(f"https://viacep.com.br/ws/{cep}/json/")
    if not data or data.get("erro"):
        return None

    return {
        "rua": data.get("logradouro", "").strip(),
        "bairro": data.get("bairro", "").strip(),
        "cidade": data.get("localidade", "").strip(),
        "estado": data.get("uf", "").strip(),
    }


def geocodificar_endereco(endereco: str):
    if not endereco:
        return None, None

    query = quote(endereco)
    data = _fetch_json(f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={query}")
    if not data:
        return None, None

    primeiro = data[0]
    try:
        latitude = Decimal(primeiro["lat"]).quantize(Decimal("0.000001"))
        longitude = Decimal(primeiro["lon"]).quantize(Decimal("0.000001"))
    except (KeyError, InvalidOperation):
        return None, None

    return latitude, longitude
