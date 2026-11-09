import requests
from bs4 import BeautifulSoup
from config import get_settings

BEO_BASE = "https://beo-procurement.iadb.org"
_LOGIN_URL = f"{BEO_BASE}/en/user/login"
_LIST_URL = f"{BEO_BASE}/en/views/activeOpportunities/view"


def _login(session: requests.Session) -> None:
    settings = get_settings()
    email = settings.beo_email
    password = settings.beo_password
    if not email or not password:
        raise RuntimeError("BEO_EMAIL y BEO_PASSWORD deben estar configurados en el .env.")

    resp = session.get(_LOGIN_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", id="user-login-form")
    if not form:
        raise RuntimeError("No se encontró el formulario de login BEO — el sitio puede haber cambiado.")

    data = {
        "name": email,
        "pass": password,
        "form_id": "user_login_form",
        "op": "Log in",
    }
    for field in ("form_build_id", "form_token"):
        el = form.find("input", {"name": field})
        if el:
            data[field] = el.get("value", "")

    login_resp = session.post(_LOGIN_URL, data=data, timeout=30, allow_redirects=True)
    if "/user/login" in login_resp.url:
        raise RuntimeError("Login BEO fallido — verificar BEO_EMAIL y BEO_PASSWORD.")


def extraer_beo() -> list[dict]:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    _login(session)

    resultados = []
    page = 1

    while True:
        resp = session.get(_LIST_URL, params={"page": page}, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        avisos = payload.get("response", [])
        if not avisos:
            break

        for a in avisos:
            nid = a.get("nid", "")
            procurement_number = a.get("field_procurement_process_number_value", "")

            deadline = (
                a.get("field_oei_deadline_date_extended_value")
                or a.get("field_deadline_date_value")
                or ""
            )

            titulo = (a.get("field_title_of_consultancy_value") or "").strip()
            proyecto = a.get("field_project_name_value", "")
            sector = a.get("sector_name", "")
            financing = a.get("field_financing_atn_value", "")

            texto = "\n".join(filter(None, [titulo, proyecto, sector, financing]))

            resultados.append({
                "id":                procurement_number,
                "institucion":       "IDB (BEO corporativo)",
                "titulo":            titulo,
                "pais":              a.get("country_name", ""),
                "proyecto":          proyecto,
                "tipo_aviso":        "Request for Expression of Interest",
                "fecha_publicacion": a.get("field_publication_date_value", ""),
                "deadline":          deadline,
                "idioma":            "Spanish/English",
                "agencia_ejecutora": "",
                "monto_estimado_usd": "",
                "contacto_email":    "",
                "link":              f"{BEO_BASE}/en/beo-active-opportunities/{nid}/reoi" if nid else "",
                "link_proyecto":     "",
                "texto_detalle":     texto,
            })

        paginator = payload.get("paginator", {})
        if page >= paginator.get("lastPage", 1):
            break
        page += 1

    return resultados
