import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

UNDP_BASE = "https://procurement-notices.undp.org"
UNDP_LIST = f"{UNDP_BASE}/index.cfm"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

_TIPOS_RELEVANTES = {"country_3", "country_4", "country_9"}


def _parse_date(texto: str) -> str:
    t = texto.strip().split("@")[0].strip()
    if not t:
        return ""
    try:
        return datetime.strptime(t, "%d-%b-%y").strftime("%Y-%m-%d")
    except ValueError:
        return t


def _parse_country(texto: str) -> str:
    t = texto.strip()
    if "/" in t:
        t = t.split("/", 1)[1].strip()
    return t.title()


def _cell_span(cell) -> str:
    span = cell.find("span")
    return span.get_text(strip=True) if span else ""


def _obtener_detalle(session: requests.Session, nego_id: str) -> tuple[str, str]:
    try:
        url = f"{UNDP_BASE}/view_negotiation.cfm?nego_id={nego_id}"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        email = ""
        for meta in soup.select("div.postMetadata__category"):
            h6 = meta.find("h6")
            if h6 and h6.get_text(strip=True) == "Contact":
                mailto = meta.find("a", href=lambda h: h and h.startswith("mailto:"))
                if mailto:
                    email = mailto["href"].replace("mailto:", "").strip()
                break

        descripcion = ""
        for div in soup.select("div.postContent"):
            h2 = div.find("h2")
            if h2 and "introduction" in h2.get_text(strip=True).lower():
                descripcion = div.get_text(separator="\n", strip=True)[:3000]
                break

        return descripcion, email
    except Exception:
        return "", ""


def extraer_undp() -> list[dict]:
    session = requests.Session()
    session.headers.update(_HEADERS)

    resp = session.get(UNDP_LIST, params={"cur_lang": "en"}, timeout=60)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("a.vacanciesTableLink.vacanciesTable__row")

    resultados = []

    for row in rows:
        clases = set(row.get("class", []))
        if not clases.intersection(_TIPOS_RELEVANTES):
            continue

        href = row.get("href", "")
        nego_id = href.split("nego_id=")[-1] if "nego_id=" in href else ""

        cells = row.select("div.vacanciesTable__cell")
        if len(cells) < 6:
            continue

        titulo    = _cell_span(cells[0])
        ref_no    = _cell_span(cells[1])
        pais_raw  = _cell_span(cells[2])
        proceso   = _cell_span(cells[3])

        nobr_deadline = cells[4].find("nobr")
        deadline = ""
        if nobr_deadline:
            first_line = nobr_deadline.get_text().split("\n")[0].strip()
            deadline = _parse_date(first_line)

        nobr_posted = cells[5].find("nobr")
        fecha_pub = _parse_date(nobr_posted.get_text(strip=True)) if nobr_posted else ""

        pais = _parse_country(pais_raw)
        link = f"{UNDP_BASE}/{href}" if href else ""

        texto_detalle, contacto_email = ("", "")
        if nego_id:
            texto_detalle, contacto_email = _obtener_detalle(session, nego_id)
            time.sleep(0.3)

        resultados.append({
            "id":                ref_no or nego_id,
            "institucion":       "UNDP",
            "titulo":            titulo,
            "pais":              pais,
            "proyecto":          ref_no,
            "tipo_aviso":        proceso,
            "fecha_publicacion": fecha_pub,
            "deadline":          deadline,
            "idioma":            "English/French/Spanish",
            "agencia_ejecutora": "",
            "monto_estimado_usd": "",
            "contacto_email":    contacto_email,
            "link":              link,
            "link_proyecto":     "",
            "texto_detalle":     texto_detalle,
        })

    return resultados
