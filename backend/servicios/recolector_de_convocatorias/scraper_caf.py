import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CAF_BASE = "https://www.caf.com"
CAF_LIST = f"{CAF_BASE}/en/work-with-us/calls/"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _parsear_deadline(texto: str) -> str:
    try:
        return datetime.strptime(texto.strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return texto.strip()


def _obtener_detalle(session: requests.Session, url: str) -> tuple[str, str]:
    try:
        resp = session.get(url, timeout=30, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        partes = []

        intro = soup.select_one("div.hero--post-convoc-licit > div")
        if intro:
            partes.append(intro.get_text(separator="\n", strip=True))

        desc = soup.select_one("div.post-convoc-licit__licit-desc")
        if desc:
            partes.append(desc.get_text(separator="\n", strip=True))

        texto = "\n\n".join(partes)[:4000]

        email = ""
        if desc:
            mailto = desc.select_one("a[href^='mailto:']")
            if mailto:
                email = mailto["href"].replace("mailto:", "").strip()

        return texto, email
    except Exception:
        return "", ""


def extraer_caf() -> list[dict]:
    session = requests.Session()
    session.headers.update(_HEADERS)

    resultados = []
    page = 1

    while True:
        resp = session.get(
            CAF_LIST,
            params={"from": "", "to": "", "enrollment": "open", "page": str(page)},
            timeout=30,
            verify=False,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select("article.card")

        if not articles:
            break

        for article in articles:
            title_tag = article.select_one("h3.card__title a")
            if not title_tag:
                continue

            titulo = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            link = f"{CAF_BASE}{href}" if href.startswith("/") else href
            slug = href.rstrip("/").split("/")[-1]

            deadline = ""
            for p in article.find_all("p"):
                texto = p.get_text()
                if "Deadline:" in texto:
                    deadline = _parsear_deadline(texto.replace("Deadline:", ""))
                    break

            tags = article.select("div.card__tags-list a")
            pais = ", ".join(t.get_text(strip=True) for t in tags) if tags else ""
            if not pais:
                overline = article.select_one("p.p-overline")
                if overline:
                    pais = overline.get_text(strip=True)

            texto_detalle, contacto_email = _obtener_detalle(session, link) if link else ("", "")

            resultados.append({
                "id":                slug,
                "institucion":       "CAF",
                "titulo":            titulo,
                "pais":              pais,
                "proyecto":          "",
                "tipo_aviso":        "Call for Consultancy",
                "fecha_publicacion": "",
                "deadline":          deadline,
                "idioma":            "English/Spanish",
                "agencia_ejecutora": "",
                "monto_estimado_usd": "",
                "contacto_email":    contacto_email,
                "link":              link,
                "link_proyecto":     "",
                "texto_detalle":     texto_detalle,
            })

        if not soup.find("a", string="Next"):
            break
        page += 1

    return resultados
