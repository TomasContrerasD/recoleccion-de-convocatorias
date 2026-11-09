import inspect
import json
import os
from datetime import datetime
from config import ConfigurationError

from .scraper_wbg import extraer_wbg
from .scraper_rfxnow import extraer_rfxnow
from .scraper_idb import extraer_idb
from .scraper_beo import extraer_beo
from .scraper_caf import extraer_caf
from .scraper_eib import extraer_eib
from .scraper_undp import extraer_undp
from .scraper_ungm import extraer_ungm
from .scraper_jbic import extraer_jbic
from .scraper_jogmec import extraer_jogmec
from .scraper_afdb import extraer_afdb
from .scraper_adb import extraer_adb
from .clasificador import clasificar_convocatoria
from .sheets_writer import escribir_en_sheets, obtener_ids_existentes, obtener_titulos_existentes_adb

RUTA_INSTITUCIONES = os.path.join(os.path.dirname(__file__), "instituciones.json")


_SCRAPERS = {
    "wbg":    extraer_wbg,
    "rfxnow": extraer_rfxnow,
    "idb":    extraer_idb,
    "beo":    extraer_beo,
    "caf":    extraer_caf,
    "eib":    extraer_eib,
    "undp":   extraer_undp,
    "ungm":   extraer_ungm,
    "jbic":   extraer_jbic,
    "jogmec": extraer_jogmec,
    "afdb":   extraer_afdb,
    "adb":    extraer_adb,
}


def _filtrar_nuevas(notices: list[dict], inst_id: str, ids: set, titulos_adb: set) -> list[dict]:
    nuevas = []
    vistos = set(ids)
    titulos_vistos = set(titulos_adb)
    for notice in notices:
        item_id = str(notice.get("id") or "").strip()
        titulo = str(notice.get("titulo") or "").strip().lower()
        if not item_id:
            raise ValueError("La fuente devolvió una convocatoria sin ID.")
        if item_id in vistos or (inst_id == "adb" and titulo in titulos_vistos):
            continue
        nuevas.append({**notice, "id": item_id})
        vistos.add(item_id)
        if inst_id == "adb":
            titulos_vistos.add(titulo)
    return nuevas


def _clasificar(aviso: dict) -> dict:
    clasificacion = clasificar_convocatoria(aviso)
    if clasificacion.get("encaje") not in {"alto", "medio", "bajo", "descartable"}:
        raise RuntimeError("No se pudo clasificar la convocatoria. Se reintentará en la próxima ejecución.")
    return clasificacion


def ejecutar_convocatorias_auto(ids: list[str] | None = None) -> dict:

    with open(RUTA_INSTITUCIONES, "r", encoding="utf-8") as f:
        todas = json.load(f)

    instituciones = [i for i in todas if i.get("activa", True)]
    if ids:
        instituciones = [i for i in instituciones if i["id"] in ids]

    try:
        ids_existentes = obtener_ids_existentes()
    except ConfigurationError as error:
        return {"guardadas": [], "total": 0, "errores": [str(error)]}
    except Exception:
        return {"guardadas": [], "total": 0, "errores": ["No se pudo leer Sheets para comprobar duplicados."]}

    try:
        titulos_adb = obtener_titulos_existentes_adb()
    except ConfigurationError as error:
        return {"guardadas": [], "total": 0, "errores": [str(error)]}
    except Exception:
        return {"guardadas": [], "total": 0, "errores": ["No se pudieron comprobar los títulos existentes en Sheets."]}

    guardadas: list[dict] = []
    errores: list[str] = []

    for inst in instituciones:
        inst_id = inst["id"]
        scraper = _SCRAPERS.get(inst_id)
        if not scraper:
            continue

        try:
            sig = inspect.signature(scraper)
            if "ids_existentes" in sig.parameters:
                notices = scraper(ids_existentes=ids_existentes)
            else:
                notices = scraper()
        except Exception as e:
            errores.append(f"{inst_id}: {e}")
            continue

        try:
            nuevas = _filtrar_nuevas(notices, inst_id, ids_existentes, titulos_adb)
        except ValueError as error:
            errores.append(f"{inst_id}: {error}")
            continue

        for aviso in nuevas:
            try:
                clasificacion = _clasificar(aviso)
                fila = {
                    **aviso,
                    **clasificacion,
                    "fecha_procesado": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                numeros = escribir_en_sheets([fila])
                fila["_fila_sheets"] = numeros[0] if numeros else None
                ids_existentes.add(aviso["id"])
                if inst_id == "adb":
                    titulos_adb.add(aviso["titulo"].strip().lower())
                guardadas.append(fila)
            except Exception as e:
                errores.append(f"guardar {aviso.get('id', '?')}: {e}")

    return {"guardadas": guardadas, "total": len(guardadas), "errores": errores}


def ejecutar_convocatorias(ids: list[str] | None = None):

    with open(RUTA_INSTITUCIONES, "r", encoding="utf-8") as f:
        todas = json.load(f)

   
    if ids:
        instituciones = [i for i in todas if i["id"] in ids and i.get("activa", True)]
    else:
        instituciones = [i for i in todas if i.get("activa", True)]

    if not instituciones:
        yield "AVISO: No hay instituciones activas para ejecutar."
        return []

    yield f"INICIO: Iniciando recopilación para {len(instituciones)} institución(es)..."

    try:
        ids_existentes = obtener_ids_existentes()
        yield f"Sheets: {len(ids_existentes)} convocatorias ya registradas."
    except ConfigurationError:
        raise
    except Exception:
        raise RuntimeError("No se pudo leer Sheets para comprobar duplicados. Intenta nuevamente.") from None

    try:
        titulos_adb = obtener_titulos_existentes_adb()
    except ConfigurationError:
        raise
    except Exception:
        raise RuntimeError("No se pudieron comprobar los títulos existentes en Sheets. Intenta nuevamente.") from None

    total_nuevas = 0
    filas_guardadas: list[dict] = []

    for inst in instituciones:
        inst_id = inst["id"]
        inst_nombre = inst["nombre"]

        yield f"\nProcesando: {inst_nombre}"

        scraper = _SCRAPERS.get(inst_id)
        if not scraper:
            yield f"  AVISO: Scraper para '{inst_id}' aún no implementado."
            continue

       
        try:
            sig = inspect.signature(scraper)
            if "ids_existentes" in sig.parameters:
                notices = scraper(ids_existentes=ids_existentes)
            else:
                notices = scraper()
            yield f"   {len(notices)} oportunidades encontradas."
        except Exception as e:
            yield f"   Error al obtener datos: {e}"
            continue

        try:
            nuevas = _filtrar_nuevas(notices, inst_id, ids_existentes, titulos_adb)
        except ValueError as error:
            yield f"   Error: {error}"
            continue
        ya_vistas = len(notices) - len(nuevas)
        if ya_vistas:
            yield f"   ⏭{ya_vistas} ya estaban en Sheets, se omiten."
        yield f"   NUEVAS:{len(nuevas)} oportunidades nuevas a clasificar."

        if not nuevas:
            yield f"   TERMINADO{inst_nombre}: sin novedades."
            continue

        
        guardadas = 0
        for aviso in nuevas:
            titulo_corto = aviso["titulo"][:70]
            yield f"   LLM: Clasificando: {titulo_corto}..."
            try:
                clasificacion = _clasificar(aviso)
                fila = {
                    **aviso,
                    **clasificacion,
                    "fecha_procesado": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                numeros = escribir_en_sheets([fila])
                fila["_fila_sheets"] = numeros[0] if numeros else None
                filas_guardadas.append(fila)
                ids_existentes.add(aviso["id"])
                if inst_id == "adb":
                    titulos_adb.add(aviso["titulo"].strip().lower())
                guardadas += 1
                yield f"   Guardada: {titulo_corto}"
            except Exception as e:
                yield f"   Error al guardar '{titulo_corto}': {e}"

        total_nuevas += guardadas
        yield f"    {inst_nombre}: {guardadas} de {len(nuevas)} convocatorias guardadas."

    if total_nuevas > 0:
        yield f"\n¡Finalizado! {total_nuevas} convocatoria(s) nueva(s) guardada(s)."
    else:
        yield "\nFIN:Proceso terminado. No se guardaron convocatorias nuevas."

    return filas_guardadas
