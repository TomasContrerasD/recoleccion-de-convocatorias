import requests
from datetime import date
from bs4 import BeautifulSoup

API_BASE = "https://search.worldbank.org/api/v2/procnotices"

_PARAMS_LISTA = {
    "format": "json",
    "fl": "id,procurement_group_desc,submission_deadline_date,bid_description,project_ctry_name,project_name,notice_type,notice_status,notice_lang_name,submission_date,noticedate",
    "srt": "noticedate",
    "order": "desc",
    "apilang": "en",
    "srce": "both",
    "procurement_group_desc_exact": "Consultant Services",
    "sector_exact": "Capital Markets^Mining",
    "notice_type_exact": "Invitation for Bids^Invitation for Prequalification^Request for Expression of Interest",
    "rows": "500",
    "os": "0",
}


def _obtener_detalle_completo(notice_id: str) -> dict:
    try:
        resp = requests.get(
            API_BASE,
            params={"format": "json", "apilang": "en", "fl": "*", "id": notice_id},
            timeout=30,
        )
        resp.raise_for_status()
        notices = resp.json().get("procnotices", [])
        return notices[0] if notices else {}
    except Exception:
        return {}


def _html_a_texto(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)


def extraer_wbg() -> list[dict]:
    params = {**_PARAMS_LISTA, "deadline_strdate": date.today().isoformat()}
    resp = requests.get(API_BASE, params=params, timeout=30)
    resp.raise_for_status()

    notices = resp.json().get("procnotices", [])
    resultados = []

    for n in notices:
        notice_id = n.get("id", "")
        detalle = _obtener_detalle_completo(notice_id)

        texto_html = detalle.get("notice_text") or detalle.get("bid_description") or ""
        texto_plano = _html_a_texto(texto_html) if texto_html else ""

        resultados.append({
            "id": notice_id,
            "institucion": "World Bank (proyectos)",
            "titulo": n.get("bid_description", ""),
            "proyecto": n.get("project_name", ""),
            "pais": n.get("project_ctry_name", ""),
            "tipo_aviso": n.get("notice_type", ""),
            "fecha_publicacion": n.get("noticedate", ""),
            "deadline": (n.get("submission_deadline_date") or "")[:10],
            "idioma": n.get("notice_lang_name", ""),
            "monto_estimado_usd": detalle.get("bid_estimate_amount", ""),
            "agencia_ejecutora": detalle.get("agency_name", ""),
            "contacto_email": detalle.get("contact_email", ""),
            "link": f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}",
            "link_proyecto": f"https://projects.worldbank.org/en/projects-operations/project-detail/{detalle.get('project_id', '')}" if detalle.get("project_id") else "",
            "texto_detalle": texto_plano,
        })

    return resultados
