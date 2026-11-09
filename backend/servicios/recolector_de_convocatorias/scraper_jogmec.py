import requests
from bs4 import BeautifulSoup
from datetime import datetime

JOGMEC_BASE = "https://www.jogmec.go.jp"
JOGMEC_LIST = f"{JOGMEC_BASE}/english/bid/search.php"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _parse_fecha(texto: str) -> str:
    texto = texto.strip()
    try:
        return datetime.strptime(texto, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return texto


def extraer_jogmec() -> list[dict]:
    resp = requests.get(JOGMEC_LIST, headers=_HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table tbody tr")

    resultados = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        fecha_pub = _parse_fecha(cells[0].get_text(strip=True))

        a_tag = cells[1].find("a")
        if not a_tag:
            continue
        titulo = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        link = f"{JOGMEC_BASE}{href}" if href.startswith("/") else href

        stem = href.split("/")[-1].replace(".html", "")
        item_id = f"jogmec-{stem}" if stem else f"jogmec-{titulo[:40]}"

        resultados.append({
            "id":                 item_id,
            "institucion":        "JOGMEC",
            "titulo":             titulo,
            "pais":               "Japón / Global",
            "proyecto":           "",
            "tipo_aviso":         "Licitación",
            "fecha_publicacion":  fecha_pub,
            "deadline":           "",
            "idioma":             "Inglés",
            "agencia_ejecutora":  "",
            "monto_estimado_usd": "",
            "contacto_email":     "",
            "link":               link,
            "link_proyecto":      JOGMEC_LIST,
            "texto_detalle":      "",
        })

    return resultados
