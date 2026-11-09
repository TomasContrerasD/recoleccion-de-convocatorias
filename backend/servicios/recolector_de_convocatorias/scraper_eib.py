import requests
from datetime import datetime

EIB_API = "https://www.eib.org/provider-eib/app/list/medias/procurements"
EIB_BASE = "https://www.eib.org"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

_SUBTYPE_PATHS = {
    "procurements-call-technical-assistance": "/en/about/procurement/calls-technical-assistance/all/",
    "procurements-call-projects-non-eu":      "/en/about/procurement/call-projects-non-eu/",
    "procurements-call-projects-eu":          "/en/about/procurement/call-projects-eu/",
    "procurements-call-advisory":             "/en/about/procurement/calls-advisory/all/",
    "procurements-call-studies":              "/en/about/procurement/calls-studies/all/",
}
_DEFAULT_PATH = "/en/about/procurement/all/"

_ITEMS_PER_PAGE = 50


def _parse_date(texto: str) -> str:
    t = texto.strip()
    if not t or t == " ":
        return ""
    try:
        return datetime.strptime(t, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return t


def _build_link(sub_type: str, url_slug: str) -> str:
    path = _SUBTYPE_PATHS.get(sub_type, _DEFAULT_PATH)
    return f"{EIB_BASE}{path}{url_slug}"


def extraer_eib() -> list[dict]:
    session = requests.Session()
    session.headers.update(_HEADERS)

    resultados = []
    page = 0

    while True:
        resp = session.get(
            EIB_API,
            params={
                "pageNumber":       str(page),
                "itemPerPage":      str(_ITEMS_PER_PAGE),
                "pageable":         "true",
                "procurementStatus": "Ongoing",
                "sortColumn":       "configuration.contentStart",
                "sortDir":          "desc",
                "la":               "EN",
            },
            timeout=30,
        )
        resp.raise_for_status()

        data = resp.json()
        items = data.get("data", []) if isinstance(data, dict) else data

        if not items:
            break

        total_items = data.get("totalItems", 0) if isinstance(data, dict) else 0

        for item in items:
            url_slug = item.get("url", "")
            titulo   = item.get("title", "").strip()
            sub_type = item.get("subType", "")
            info     = item.get("additionalInformation", [])

            tipo_aviso        = info[1].strip() if len(info) > 1 else ""
            referencia        = info[2].strip() if len(info) > 2 else ""
            fecha_publicacion = _parse_date(info[3]) if len(info) > 3 else ""
            deadline          = _parse_date(info[4]) if len(info) > 4 else ""

            pais = ""
            if item.get("country"):
                c = item["country"]
                pais = c.get("name", "") if isinstance(c, dict) else str(c)

            link = _build_link(sub_type, url_slug) if url_slug else ""

            resultados.append({
                "id":                url_slug,
                "institucion":       "EIB",
                "titulo":            titulo,
                "pais":              pais,
                "proyecto":          referencia,
                "tipo_aviso":        tipo_aviso,
                "fecha_publicacion": fecha_publicacion,
                "deadline":          deadline,
                "idioma":            "English",
                "agencia_ejecutora": "",
                "monto_estimado_usd": "",
                "contacto_email":    "",
                "link":              link,
                "link_proyecto":     "",
                "texto_detalle":     "",
            })

        if total_items and len(resultados) >= total_items:
            break
        if len(items) < _ITEMS_PER_PAGE:
            break
        page += 1

    return resultados
