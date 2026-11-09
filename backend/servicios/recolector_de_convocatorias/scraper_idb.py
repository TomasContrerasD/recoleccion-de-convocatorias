import requests
from datetime import datetime, timezone

API_BASE = "https://bidfa-admin.connectamericas.com/items/tenders"

_PAIS_PREFIJO = {
    "AR": "Argentina",
    "BA": "Barbados",
    "BE": "Belize",
    "BO": "Bolivia",
    "BR": "Brazil",
    "CH": "Chile",
    "CO": "Colombia",
    "CR": "Costa Rica",
    "DR": "Dominican Republic",
    "EC": "Ecuador",
    "ES": "El Salvador",
    "GU": "Guatemala",
    "GY": "Guyana",
    "HA": "Haiti",
    "HN": "Honduras",
    "JA": "Jamaica",
    "ME": "Mexico",
    "NI": "Nicaragua",
    "PN": "Panama",
    "PE": "Peru",
    "PR": "Paraguay",
    "RG": "Regional",
    "SU": "Suriname",
    "TT": "Trinidad and Tobago",
    "UR": "Uruguay",
    "VE": "Venezuela",
}

_TIPO_AVISO = {
    "1": "Request for Expression of Interest",
    "2": "Request for Proposals",
    "3": "Invitation for Bids",
    "4": "Request for Quotations",
    "5": "Invitation for Prequalification",
    "6": "Invitation for Bids",
}


def _pais_desde_proyecto(project_number: str) -> str:
    prefijo = (project_number or "")[:2].upper()
    return _PAIS_PREFIJO.get(prefijo, "")


def _titulo_desde_search_index(search_index: str) -> str:
    for line in (search_index or "").split("\n"):
        line = line.strip()
        if line:
            return line[:500]
    return ""


def extraer_idb() -> list[dict]:
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    resp = requests.get(
        API_BASE,
        params={
            "filter[status]": "approved",
            "limit": "501",
            "filter[date_close][_gte]": today_iso,
        },
        timeout=30,
    )
    resp.raise_for_status()

    avisos = resp.json().get("data", [])
    resultados = []

    for a in avisos:
        aviso_id = str(a.get("id", ""))
        project_number = a.get("project_number", "")
        interest_expression = str(a.get("interest_expression", ""))
        date_close = a.get("date_close", "")
        date_created = a.get("date_created", "")
        search_index = a.get("search_index", "")

        resultados.append({
            "id":                aviso_id,
            "institucion":       "IDB (proyectos)",
            "titulo":            _titulo_desde_search_index(search_index),
            "pais":              _pais_desde_proyecto(project_number),
            "proyecto":          project_number,
            "tipo_aviso":        _TIPO_AVISO.get(interest_expression, "Tender"),
            "fecha_publicacion": date_created[:10] if date_created else "",
            "deadline":          date_close[:10] if date_close else "",
            "idioma":            "Spanish/English",
            "agencia_ejecutora": "",
            "monto_estimado_usd": "",
            "contacto_email":    a.get("contact_email", ""),
            "link":              a.get("tender_url", ""),
            "link_proyecto":     a.get("project_url", ""),
            "texto_detalle":     search_index,
        })

    return resultados
