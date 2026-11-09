import re
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
from .ia import traducir_textos

EDCF_BASE   = "https://www.edcfkorea.go.kr"
EDCF_LIST   = f"{EDCF_BASE}/fe/HPHFFE065M01"
EDCF_DETAIL = f"{EDCF_BASE}/fe/HPHFFE066M01"

_SECTORES = ["에너지", "환경·위생", "기타"]

_PAGE_SIZE = 10
_MAX_PAGES = 30

_TIPO_ES = {
    "개도국발주사업": "Proyecto licitado por país receptor",
    "EDCF발주사업":   "Proyecto EDCF (contratación directa)",
    "KSP사업":        "Proyecto KSP",
}
_SECTOR_ES = {
    "에너지":        "Energía",
    "환경·위생":     "Medio ambiente y saneamiento",
    "기타":          "Otros",
    "IT":            "IT",
    "교통":          "Transporte",
    "보건·의료":     "Salud y medicina",
    "인적자원개발":  "Desarrollo de recursos humanos",
}

def _parse_fecha(texto: str) -> str:
    return texto.strip().replace(".", "-")


def _extract_boardid(href: str) -> str:
    m = re.search(r"boardid=(\d+)", href)
    return m.group(1) if m else ""


def _traducir_batch(textos_ko: list[str]) -> list[str]:
    return traducir_textos(textos_ko, "coreano")


def _scrape_sector(session: cffi_requests.Session, sector: str) -> list[dict]:
    items = []
    page = 1

    while page <= _MAX_PAGES:
        data = {
            "boardtext2":   "",
            "boardtext8":   "",
            "boardtext9":   sector,
            "boardtypeid":  "162",
            "isIframe":     "N",
            "menuid":       "",
            "ssnreturl":    "./form?boardtypeid=162&menuid=",
            "searchselect": "",
            "searchword":   "",
            "pagesize":     str(_PAGE_SIZE),
            "currentpage":  str(page),
        }
        resp = session.post(EDCF_LIST, data=data, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("div.notice-list-item")

        if not rows:
            break

        for row in rows:
            spans = row.find_all("span", recursive=False)
            if len(spans) < 7:
                continue

            badge   = spans[1].select_one("span.cate-badge")
            tipo_ko = badge.get_text(strip=True) if badge else ""

            sec_a     = spans[2].find("a")
            sector_ko = sec_a.get_text(strip=True) if sec_a else ""

            country_a = spans[3].find("a")
            pais_ko   = country_a.get_text(strip=True) if country_a else ""

            title_a   = spans[4].find("a")
            titulo_ko = title_a.get_text(strip=True) if title_a else ""
            href      = title_a.get("href", "") if title_a else ""
            boardid   = _extract_boardid(href)
            link      = f"{EDCF_DETAIL}?boardtypeid=162&boardid={boardid}" if boardid else ""

            date_span = spans[6]
            blind = date_span.find("span", class_="blind")
            if blind:
                blind.decompose()
            fecha = _parse_fecha(date_span.get_text(strip=True))

            if not titulo_ko or not boardid:
                continue

            items.append({
                "id":                f"edcf-{boardid}",
                "_titulo_ko":        titulo_ko,
                "_pais_ko":          pais_ko,
                "tipo_aviso":        _TIPO_ES.get(tipo_ko, tipo_ko),
                "agencia_ejecutora": _SECTOR_ES.get(sector_ko, sector_ko),
                "fecha_publicacion": fecha,
                "link":              link,
            })

        if len(rows) < _PAGE_SIZE:
            break
        page += 1

    return items


def extraer_edcf() -> list[dict]:
    session = cffi_requests.Session(impersonate="chrome")

    items_raw = []
    seen_ids  = set()

    for sector in _SECTORES:
        for item in _scrape_sector(session, sector):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                items_raw.append(item)

    if not items_raw:
        return []

    titulos_ko = [item["_titulo_ko"] for item in items_raw]
    paises_ko  = [item["_pais_ko"]   for item in items_raw]
    traducidos = _traducir_batch(titulos_ko + paises_ko)
    n = len(items_raw)
    titulos_es = traducidos[:n]
    paises_es  = traducidos[n:]

    resultados = []
    for item, titulo_es, pais_es in zip(items_raw, titulos_es, paises_es):
        resultados.append({
            "id":                 item["id"],
            "institucion":        "EDCF",
            "titulo":             titulo_es,
            "pais":               pais_es or "Global",
            "proyecto":           "",
            "tipo_aviso":         item["tipo_aviso"],
            "fecha_publicacion":  item["fecha_publicacion"],
            "deadline":           "",
            "idioma":             "Coreano",
            "agencia_ejecutora":  item["agencia_ejecutora"],
            "monto_estimado_usd": "",
            "contacto_email":     "",
            "link":               item["link"],
            "link_proyecto":      EDCF_LIST,
            "texto_detalle":      "",
        })

    return resultados
