import requests
from bs4 import BeautifulSoup

API_URL = "https://wbgeprocure-rfxnow.worldbank.org/rfxnow/json/advertisement/activeAdvertisements.json"


def _institucion_desde_email(email: str) -> str:
    if "@ifc.org" in email:
        return "IFC"
    elif "@worldbank.org" in email or "@worldbankgroup.org" in email:
        return "World Bank (corporativo)"
    elif "@miga.org" in email:
        return "MIGA"
    else:
        dominio = email.split("@")[-1].split(".")[0].upper() if "@" in email else "WBG"
        return dominio


def extraer_rfxnow() -> list[dict]:
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()

    avisos = resp.json().get("advertisementList", [])
    resultados = []

    for a in avisos:
        email = (
            a.get("createdBy", {})
            .get("userProfile", {})
            .get("email", "")
        )
        texto_html = a.get("text", "")
        texto_plano = (
            BeautifulSoup(texto_html, "html.parser").get_text(separator="\n", strip=True)
            if texto_html else ""
        )

        aviso_id = str(a.get("id", ""))
        procurement_number = str(a.get("procurementId", a.get("procurementNumber", aviso_id)))

        deadline_raw = a.get("eoiDeadline") or a.get("extendedDeadlineProposal") or ""
        deadline = deadline_raw[:10] if deadline_raw else ""

        resultados.append({
            "id":               procurement_number,
            "institucion":      _institucion_desde_email(email),
            "titulo":           a.get("procurementTitle", ""),
            "pais":             "",
            "proyecto":         "",
            "tipo_aviso":       "Request for Expression of Interest",
            "fecha_publicacion": (a.get("publicationDate") or "")[:10],
            "deadline":         deadline,
            "idioma":           "English",
            "agencia_ejecutora": "",
            "monto_estimado_usd": "",
            "contacto_email":   email,
            "link":             f"https://wbgeprocure-rfxnow.worldbank.org/rfxnow/public/advertisement/{aviso_id}/view.html",
            "link_proyecto":    "",
            "texto_detalle":    texto_plano,
        })

    return resultados
