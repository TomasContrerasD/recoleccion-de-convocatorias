import re
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from datetime import datetime

AIIB_BASE = "https://www.aiib.org"
AIIB_LIST = (
    f"{AIIB_BASE}/en/opportunities/business/corporate-procurement"
    "/list/status/open/section/All/type/All"
)


def _parse_date(texto: str) -> str:
    t = texto.strip()
    try:
        return datetime.strptime(t, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return t


def _ariba_id(href: str) -> str:
    m = re.search(r"RfxEvent/preview/(\d+)", href)
    return m.group(1) if m else ""


def extraer_aiib() -> list[dict]:
    session = cffi_requests.Session(impersonate="chrome")

    resp = session.get(AIIB_LIST, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    rows = soup.select("ul.table-row.row")

    resultados = []

    for row in rows:
        issue_date = ""
        deadline = ""
        date_cell = row.select_one("li.table-date")
        if date_cell:
            issue_div = date_cell.select_one("div.issue-date")
            if issue_div:
                raw = issue_div.get_text(separator=" ", strip=True)
                raw = raw.replace("ISSUE DATE:", "").strip()
                if raw:
                    issue_date = _parse_date(raw)

            closing_span = date_cell.select_one("div.closing-date span.s2")
            if closing_span:
                deadline = _parse_date(closing_span.get_text(strip=True))

        titulo = ""
        link = ""
        project_cell = row.select_one("li.table-project")
        if project_cell:
            title_span = project_cell.select_one("span.s1")
            if title_span:
                titulo = title_span.get_text(separator=" ", strip=True)

            more_a = project_cell.select_one("a")
            if more_a:
                link = more_a.get("href", "")

        if not titulo:
            continue

        status = ""
        status_cell = row.select_one("li.table-status")
        if status_cell:
            status = status_cell.get_text(strip=True)

        section = ""
        section_cell = row.select_one("li.table-section")
        if section_cell:
            section = section_cell.get_text(strip=True)

        tipo = ""
        type_cell = row.select_one("li.table-type")
        if type_cell:
            tipo = type_cell.get_text(strip=True)

        ariba = _ariba_id(link)
        item_id = f"aiib-{ariba}" if ariba else f"aiib-{titulo[:50].lower().replace(' ', '-')}"

        resultados.append({
            "id":                 item_id,
            "institucion":        "AIIB",
            "titulo":             titulo,
            "pais":               "Global",
            "proyecto":           section,
            "tipo_aviso":         tipo,
            "fecha_publicacion":  issue_date,
            "deadline":           deadline,
            "idioma":             "English",
            "agencia_ejecutora":  "",
            "monto_estimado_usd": "",
            "contacto_email":     "",
            "link":               link,
            "link_proyecto":      f"{AIIB_LIST}",
            "texto_detalle":      "",
        })

    return resultados
