import re
import requests
from bs4 import BeautifulSoup
from .ia import traducir_textos

JBIC_BASE = "https://www.jbic.go.jp"

_PAGINAS = [
    ("Licitación general (一般競争入札)", f"{JBIC_BASE}/ja/info/bid-general.html"),
    ("Convocatoria pública (公募)",       f"{JBIC_BASE}/ja/info/bid-public.html"),
    ("Concurso de planificación (企画競争)", f"{JBIC_BASE}/ja/info/bid-plan.html"),
]

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def _parse_fecha_jp(texto: str) -> str:
    texto = texto.replace("\n", "").strip()
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", texto)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return texto


def _traducir_titulos(titulos_jp: list[str]) -> list[str]:
    return traducir_textos(titulos_jp, "japonés")


def extraer_jbic() -> list[dict]:
    session = requests.Session()
    session.headers.update(_HEADERS)

    items_raw = []

    for tipo_aviso, url in _PAGINAS:
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            fecha_pub = _parse_fecha_jp(cells[0].get_text(separator="\n"))

            a_tag = cells[1].find("a")
            titulo_jp = (
                a_tag.get_text(strip=True) if a_tag
                else cells[1].get_text(strip=True)
            )
            href = a_tag.get("href", "") if a_tag else ""
            link = f"{JBIC_BASE}{href}" if href.startswith("/") else href

            deadline = _parse_fecha_jp(cells[2].get_text(separator="\n"))

            if not titulo_jp:
                continue

            pdf_stem = href.split("/")[-1].replace(".pdf", "") if href else ""
            item_id = f"jbic-{pdf_stem}" if pdf_stem else f"jbic-{titulo_jp[:40]}"

            items_raw.append({
                "id":                 item_id,
                "_titulo_jp":         titulo_jp,
                "institucion":        "JBIC",
                "pais":               "Japón / Global",
                "proyecto":           "",
                "tipo_aviso":         tipo_aviso,
                "fecha_publicacion":  fecha_pub,
                "deadline":           deadline,
                "idioma":             "Japonés",
                "agencia_ejecutora":  "",
                "monto_estimado_usd": "",
                "contacto_email":     "",
                "link":               link,
                "link_proyecto":      f"{JBIC_BASE}/ja/info.html",
                "texto_detalle":      "",
            })

    if not items_raw:
        return []

    titulos_jp = [item["_titulo_jp"] for item in items_raw]
    titulos_es = _traducir_titulos(titulos_jp)

    resultados = []
    for item, titulo_es in zip(items_raw, titulos_es):
        item.pop("_titulo_jp")
        resultados.append({**item, "titulo": titulo_es})

    return resultados
