import re
from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import date, datetime

AFDB_BASE = "https://www.afdb.org"
AFDB_LIST = f"{AFDB_BASE}/en/about-us/corporate-procurement/procurement-notices/current-solicitations"
_PAGE_SIZE = 18
_MAX_PAGES = 60

_TIPO_AVISO = {
    "ITB": "Invitation to Bid",
    "RFP": "Request for Proposals",
    "RPF": "Demande de Propositions",
    "RFQ": "Request for Quotations",
}


def _parse_iso(content_attr: str) -> str:
    return content_attr[:10] if content_attr else ""


def _normalizar_id(referencia: str) -> str:
    return "afdb-" + referencia.replace("/", "-").strip()


def _fetch_detalle(session, url: str) -> dict:
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        body_div = soup.select_one(".field-name-body .field-item.even")
        texto = " ".join(p.get_text(strip=True) for p in body_div.find_all("p")) if body_div else ""

        email = ""
        m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", texto)
        if m:
            email = m.group(0)

        pdf_a = soup.select_one(".field-name-field-ifb-document .field-item a[href]")
        link_pdf = pdf_a.get("href", "") if pdf_a else ""

        return {"texto_detalle": texto, "contacto_email": email, "link_pdf": link_pdf}
    except Exception:
        return {}


def extraer_afdb(ids_existentes: set | None = None) -> list[dict]:
    session = requests.Session(impersonate="chrome")

    hoy = date.today()
    resultados: list[dict] = []
    seen_ids: set[str] = set()

    for page in range(_MAX_PAGES):
        params = {"title": "", "tid": "All", "tid_1": "All", "page": page}
        resp = session.get(AFDB_LIST, params=params, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("#views-bootstrap-grid-1 .col-xs-12.col-sm-12.col-md-4")

        if not cards:
            break

        activas_en_pagina = 0

        for card in cards:
            a_tag = card.select_one(".views-field-title .field-content a")
            if not a_tag:
                continue
            titulo = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            link = f"{AFDB_BASE}{href}" if href.startswith("/") else href

            ref_div = card.select_one(".views-field-field-procurement-reference .field-content")
            referencia = ref_div.get_text(strip=True) if ref_div else ""
            item_id = _normalizar_id(referencia) if referencia else f"afdb-{href.split('/')[-1]}"

            if item_id in seen_ids:
                continue

            pub_span = card.select_one(".views-field-field-procurement-pub-date .field-content span")
            fecha_pub = _parse_iso(pub_span.get("content", "")) if pub_span else ""

            dead_span = card.select_one(".views-field-field-procurement-end-date .field-content span")
            deadline_str = _parse_iso(dead_span.get("content", "")) if dead_span else ""

            if deadline_str:
                try:
                    if datetime.strptime(deadline_str, "%Y-%m-%d").date() < hoy:
                        continue
                except ValueError:
                    pass

            activas_en_pagina += 1
            seen_ids.add(item_id)

            tipo_aviso = ""
            if referencia and "/" in referencia:
                partes = referencia.split("/")
                if len(partes) >= 2:
                    tipo_aviso = _TIPO_AVISO.get(partes[1], partes[1])

            detalle = {}
            if ids_existentes is None or item_id not in ids_existentes:
                detalle = _fetch_detalle(session, link)

            link_final = detalle.get("link_pdf") or link

            resultados.append({
                "id":                 item_id,
                "institucion":        "AfDB",
                "titulo":             titulo,
                "pais":               "África",
                "proyecto":           referencia,
                "tipo_aviso":         tipo_aviso,
                "fecha_publicacion":  fecha_pub,
                "deadline":           deadline_str,
                "idioma":             "Inglés / Francés",
                "agencia_ejecutora":  "",
                "monto_estimado_usd": "",
                "contacto_email":     detalle.get("contacto_email", ""),
                "link":               link_final,
                "link_proyecto":      AFDB_LIST,
                "texto_detalle":      detalle.get("texto_detalle", ""),
            })

        if len(cards) == _PAGE_SIZE and activas_en_pagina == 0:
            break

        if len(cards) < _PAGE_SIZE:
            break

    return resultados
