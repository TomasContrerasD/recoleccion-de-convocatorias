import re
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime

ADB_BASE = "https://selfservice.adb.org"
ADB_LIST = f"{ADB_BASE}/OA_HTML/OA.jsp"
_PARAMS = {"OAFunc": "XXCRS_CSRN_HOME_PAGE"}
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_PAGE_SIZE = 25
_MAX_PAGES = 12

_PAISES = {
    "AFG": "Afganistán",    "ARM": "Armenia",        "AZE": "Azerbaiyán",
    "BAN": "Bangladesh",    "BHU": "Bután",           "CAM": "Camboya",
    "PRC": "China",         "COO": "Islas Cook",      "FIJ": "Fiyi",
    "GEO": "Georgia",       "IND": "India",           "INO": "Indonesia",
    "KAZ": "Kazajistán",    "KIR": "Kiribati",        "KGZ": "Kirguistán",
    "LAO": "Laos",          "MAL": "Malasia",         "MLD": "Maldivas",
    "MON": "Mongolia",      "MYA": "Myanmar",         "NAU": "Nauru",
    "NEP": "Nepal",         "PAK": "Pakistán",        "PAL": "Palau",
    "PNG": "Papúa Nueva Guinea", "PHI": "Filipinas",  "SAM": "Samoa",
    "SRI": "Sri Lanka",     "TAJ": "Tayikistán",      "THA": "Tailandia",
    "TIM": "Timor Oriental","TON": "Tonga",           "TUV": "Tuvalu",
    "UZB": "Uzbekistán",    "VAN": "Vanuatu",         "VIE": "Vietnam",
    "REG": "Regional (Asia-Pacífico)",
}


def _parse_fecha(texto: str) -> str:
   
    try:
        return datetime.strptime(texto.strip(), "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return texto.strip()


def _parse_deadline(texto: str) -> str:
    
    partes = texto.strip().split()
    if partes:
        try:
            return datetime.strptime(partes[0], "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def _extraer_pais(titulo: str) -> str:
   
    m = re.search(r"\b([A-Z]{3}): ", titulo)
    if m:
        return _PAISES.get(m.group(1), m.group(1))
    return "Asia-Pacífico"


def _parse_pagina(soup: BeautifulSoup, hoy: date) -> list[dict]:
    
    resultados = []

    for a_proj in soup.select("a[id^='atResults:mstProject:']"):
        tr = a_proj.find_parent("tr")
        if not tr:
            continue

        titulo = a_proj.get("title", "").strip()
        link = a_proj.get("href", "")

        idx_m = re.search(r":mstProject:(\d+)$", a_proj.get("id", ""))
        idx = idx_m.group(1) if idx_m else ""

        sp_exp = tr.select_one(f"span[id='atResults:mstExpertise2:{idx}']")
        expertise = sp_exp.get_text(strip=True) if sp_exp else ""

        sp_type = tr.select_one(f"span[id='atResults:mcConsType:{idx}'] span.x4")
        cons_type = sp_type.get_text(strip=True) if sp_type else ""

        sp_pub = tr.select_one(f"span[id='atResults:mstPublished:{idx}']")
        fecha_pub = _parse_fecha(sp_pub.get_text(strip=True)) if sp_pub else ""

        sp_dead = tr.select_one(f"span[id='atResults:mstDeadline:{idx}']")
        deadline_str = _parse_deadline(sp_dead.get_text(strip=True)) if sp_dead else ""

        if deadline_str:
            try:
                if datetime.strptime(deadline_str, "%Y-%m-%d").date() < hoy:
                    continue
            except ValueError:
                pass

        
        a_csrn = tr.select_one(f"a[id='atResults:imgCsrn:{idx}']")
        csrn_id = ""
        if a_csrn:
            m = re.search(r"CsrnResultVO1(\d+)", a_csrn.get("onclick", ""))
            if m:
                csrn_id = m.group(1)
        if not csrn_id:
            
            slug = link.rstrip("/").split("/")[-2] if link else ""
            csrn_id = f"{slug}-{idx}"

        resultados.append({
            "id":                 f"adb-{csrn_id}",
            "institucion":        "ADB",
            "titulo":             titulo,
            "pais":               _extraer_pais(titulo),
            "proyecto":           expertise,
            "tipo_aviso":         cons_type,
            "fecha_publicacion":  fecha_pub,
            "deadline":           deadline_str,
            "idioma":             "Inglés",
            "agencia_ejecutora":  "",
            "monto_estimado_usd": "",
            "contacto_email":     "",
            "link":               link,
            "link_proyecto":      f"{ADB_LIST}?OAFunc=XXCRS_CSRN_HOME_PAGE",
            "texto_detalle":      expertise,
        })

    return resultados


def extraer_adb() -> list[dict]:
    
    session = requests.Session()
    session.headers.update(_HEADERS)

    hoy = date.today()
    resultados: list[dict] = []
    seen_ids: set[str] = set()

    resp = session.get(ADB_LIST, params=_PARAMS, timeout=30)
    resp.raise_for_status()

    for page_num in range(_MAX_PAGES):
        soup = BeautifulSoup(resp.text, "html.parser")

        for r in _parse_pagina(soup, hoy):
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                resultados.append(r)

        n_rows = len(soup.select("a[id^='atResults:mstProject:']"))
        if n_rows < _PAGE_SIZE:
            break

        
        next_start = (page_num + 1) * _PAGE_SIZE + 1
        form_data: dict[str, str] = {}
        for inp in soup.select("input[type='hidden']"):
            name = inp.get("name")
            if name:
                form_data[name] = inp.get("value", "")
        form_data["M__Idxxb"] = f"{next_start},{_PAGE_SIZE}"

        try:
            resp = session.post(ADB_LIST, params=_PARAMS, data=form_data, timeout=30)
            resp.raise_for_status()
            if "atResults:mstProject:" not in resp.text:
                break
        except Exception:
            break

    return resultados
