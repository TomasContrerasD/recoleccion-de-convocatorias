import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

EBRD_BASE = "https://ecepp.ebrd.com/delta"
EBRD_LIST = f"{EBRD_BASE}/noticeSearchResults.html"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _parse_fecha(texto: str) -> str:
    texto = texto.strip()[:10]
    try:
        return datetime.strptime(texto, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return texto


def _fetch_detalle(session: requests.Session, url: str) -> dict:
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tabla = soup.select_one("#oppoverviewtable")
        if not tabla:
            return {}

        campos = {}
        for row in tabla.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True).rstrip(":")
            valor = cells[1].get_text(strip=True)
            campos[label] = valor

        cuerpo = soup.select_one("div.completeentry")
        email = ""
        if cuerpo:
            m = re.search(r"Email:\s*([\w.+-]+@[\w.-]+\.\w+)", cuerpo.get_text())
            if m:
                email = m.group(1)

        return {
            "proyecto":          campos.get("Project Name", ""),
            "agencia_ejecutora": campos.get("Business Sector", ""),
            "texto_detalle":     campos.get("Procurement Exercise Description", ""),
            "contacto_email":    email,
        }
    except Exception:
        return {}


def extraer_ebrd(ids_existentes: set | None = None) -> list[dict]:
    session = requests.Session()
    session.headers.update(_HEADERS)

    resp = session.get(EBRD_LIST, timeout=60)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("#noticeResultsTable tbody tr")

    resultados = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        current_state = cells[5].get_text(strip=True)
        if current_state != "Open":
            continue

        a_tag = cells[0].find("a")
        if not a_tag:
            continue
        titulo_raw = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        link = f"{EBRD_BASE}/{href}" if not href.startswith("http") else href

        m = re.search(r"displayNoticeId=(\d+)", href)
        item_id = f"ebrd-{m.group(1)}" if m else f"ebrd-{titulo_raw[:40]}"

        if ": " in titulo_raw:
            pais, titulo = titulo_raw.split(": ", 1)
        else:
            pais, titulo = "", titulo_raw

        notice_type  = cells[1].get_text(strip=True)
        ejercicio    = cells[2].get_text(strip=True)
        fecha_pub    = _parse_fecha(cells[3].get_text(separator=" ", strip=True))
        deadline_raw = cells[4].get_text(separator=" ", strip=True)
        deadline     = _parse_fecha(deadline_raw) if "N/A" not in deadline_raw else ""

        detalle: dict = {}
        if ids_existentes is None or item_id not in ids_existentes:
            detalle = _fetch_detalle(session, link)
            time.sleep(0.3)

        resultados.append({
            "id":                 item_id,
            "institucion":        "EBRD",
            "titulo":             titulo,
            "pais":               pais,
            "proyecto":           detalle.get("proyecto", ""),
            "tipo_aviso":         notice_type,
            "fecha_publicacion":  fecha_pub,
            "deadline":           deadline,
            "idioma":             "Inglés",
            "agencia_ejecutora":  detalle.get("agencia_ejecutora", ""),
            "monto_estimado_usd": "",
            "contacto_email":     detalle.get("contacto_email", ""),
            "link":               link,
            "link_proyecto":      EBRD_LIST,
            "texto_detalle":      detalle.get("texto_detalle", ejercicio),
        })

    return resultados
