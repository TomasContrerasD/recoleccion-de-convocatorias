import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

UNGM_BASE   = "https://www.ungm.org"
UNGM_LIST   = f"{UNGM_BASE}/Public/Notice"
UNGM_SEARCH = f"{UNGM_BASE}/Public/Notice/Search"

_HEADERS = {
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/json",
    "Accept":       "*/*",
}

_NOTICE_TYPES = [
    "RequestForProposal",
    "RequestForEOI",
    "GrantSupportCallForProposal",
]

_PAGE_SIZE = 50

_MESES_ES = {
    1: "ene.", 2: "feb.", 3: "mar.", 4: "abr.",
    5: "may.", 6: "jun.", 7: "jul.", 8: "ago.",
    9: "sep.", 10: "oct.", 11: "nov.", 12: "dic.",
}
_MESES_ES_INV = {v: k for k, v in _MESES_ES.items()}


def _fecha_ungm(dt: datetime) -> str:
    return f"{dt.day:02d}-{_MESES_ES[dt.month]}-{dt.year}"


def _parse_fecha(texto: str) -> str:
    partes = texto.strip().split()
    if not partes:
        return ""
    t = partes[0]
    parts = t.split("-")
    if len(parts) != 3:
        return t
    try:
        day   = int(parts[0])
        month = _MESES_ES_INV.get(parts[1], 0)
        year  = int(parts[2])
        if month:
            return datetime(year, month, day).strftime("%Y-%m-%d")
    except Exception:
        pass
    return t


def extraer_ungm() -> list[dict]:
    session = requests.Session()
    session.headers.update(_HEADERS)

    resp_init = session.get(UNGM_LIST, timeout=30)
    soup_init = BeautifulSoup(resp_init.text, "html.parser")
    token_input = soup_init.find("input", {"name": "__RequestVerificationToken"})
    if token_input:
        session.headers["RequestVerificationToken"] = token_input.get("value", "")

    today = datetime.now()
    resultados = []
    page = 0

    while True:
        payload = {
            "PageIndex":                  page,
            "PageSize":                   _PAGE_SIZE,
            "Title":                      "",
            "Description":                "",
            "Reference":                  "",
            "PublishedFrom":              "",
            "PublishedTo":                "",
            "DeadlineFrom":               _fecha_ungm(today),
            "DeadlineTo":                 "",
            "IsActive":                   True,
            "IsSustainable":              False,
            "NoticeDisplayType":          None,
            "NoticeSearchTotalLabelId":   "noticeSearchTotal",
            "NoticeTypes":                _NOTICE_TYPES,
            "SortAscending":              True,
            "SortField":                  "Deadline",
            "Agencies":                   [],
            "Countries":                  [],
            "TypeOfCompetitions":         [],
            "UNSPSCs":                    [],
            "isPicker":                   False,
        }

        resp = session.post(UNGM_SEARCH, json=payload, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("div.tableRow.dataRow.notice-table")

        if not rows:
            break

        for row in rows:
            notice_id = row.get("data-noticeid", "")

            titulo = ""
            title_span = row.select_one(".resultTitle .ungm-title")
            if title_span:
                titulo = title_span.get_text(strip=True)

            deadline = ""
            deadline_cell = row.select_one(".tableCell.resultInfo1.deadline")
            if deadline_cell:
                for span in deadline_cell.find_all("span"):
                    if "remainingDaysToDeadline" not in span.get("class", []):
                        raw = span.get_text().strip().split("\n")[0].strip()
                        if raw:
                            deadline = _parse_fecha(raw)
                            break

            fecha_pub = ""
            all_cells = row.select("div.tableCell")
            if len(all_cells) >= 4:
                pub_span = all_cells[3].find("span")
                if pub_span:
                    fecha_pub = _parse_fecha(pub_span.get_text(strip=True))

            organizacion = ""
            org_span = row.select_one(".tableCell.resultAgency span")
            if org_span:
                organizacion = org_span.get_text(strip=True)

            tipo_aviso = ""
            tipo_label = row.select_one(".tableCell label")
            if tipo_label:
                tipo_aviso = tipo_label.get_text(strip=True)

            ref_no = ""
            ref_cell = row.select_one('.tableCell.resultInfo1[data-description="Referencia"] span')
            if ref_cell:
                ref_no = ref_cell.get_text(strip=True)

            pais = ""
            if all_cells:
                country_span = all_cells[-1].find("span")
                if country_span:
                    pais = country_span.get_text(strip=True)

            link = f"{UNGM_LIST}/{notice_id}" if notice_id else ""

            resultados.append({
                "id":                ref_no or notice_id,
                "institucion":       "UNGM",
                "titulo":            titulo,
                "pais":              pais,
                "proyecto":          ref_no,
                "tipo_aviso":        tipo_aviso,
                "fecha_publicacion": fecha_pub,
                "deadline":          deadline,
                "idioma":            "English/French/Spanish",
                "agencia_ejecutora": organizacion,
                "monto_estimado_usd": "",
                "contacto_email":    "",
                "link":              link,
                "link_proyecto":     "",
                "texto_detalle":     "",
            })

        if len(rows) < _PAGE_SIZE:
            break
        page += 1
        time.sleep(0.5)

    return resultados
