import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import ConfigurationError, get_settings

COLUMNAS = [
    "ID",
    "Fecha Procesado",
    "Institución",
    "País",
    "Título",
    "Proyecto",
    "Agencia Ejecutora",
    "Tipo Aviso",
    "Fecha Publicación",
    "Deadline",
    "Idioma",
    "Monto Estimado (USD)",
    "Link",
    "Link Proyecto",
    "Encaje",
    "Contacto Email",
]


_CAMPO_A_CLAVE = {
    "ID":                   "id",
    "Fecha Procesado":      "fecha_procesado",
    "Institución":          "institucion",
    "País":                 "pais",
    "Título":               "titulo",
    "Proyecto":             "proyecto",
    "Agencia Ejecutora":    "agencia_ejecutora",
    "Tipo Aviso":           "tipo_aviso",
    "Fecha Publicación":    "fecha_publicacion",
    "Deadline":             "deadline",
    "Idioma":               "idioma",
    "Monto Estimado (USD)": "monto_estimado_usd",
    "Link":                 "link",
    "Link Proyecto":        "link_proyecto",
    "Encaje":               "encaje",
    "Contacto Email":       "contacto_email",
}


def _conectar_sheets():
    settings = get_settings()
    if not settings.sheets_id:
        raise ConfigurationError("Configura SHEETS_CONVOCATORIAS_ID en backend/.env.")
    permisos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    
    creds_path = settings.google_application_credentials
    if creds_path.is_file():
        creds = ServiceAccountCredentials.from_json_keyfile_name(str(creds_path), permisos)
    else:
        creds_json = settings.google_credentials_json
        if not creds_json:
            raise ConfigurationError(
                "Configura GOOGLE_APPLICATION_CREDENTIALS o GOOGLE_CREDENTIALS_JSON en backend/.env."
            )
        try:
            credentials_data = json.loads(creds_json)
        except json.JSONDecodeError:
            raise ConfigurationError("GOOGLE_CREDENTIALS_JSON debe contener JSON valido.") from None
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_data, permisos)

    client = gspread.authorize(creds)
    sheet = client.open_by_key(settings.sheets_id)

    
    try:
        ws = sheet.worksheet(settings.sheets_tab_name)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=settings.sheets_tab_name, rows=1000, cols=len(COLUMNAS))
        ws.append_row(COLUMNAS)
        return ws

    encabezados = ws.row_values(1)
    if not encabezados:
        ws.update(values=[COLUMNAS], range_name=f"A1:{gspread.utils.rowcol_to_a1(1, len(COLUMNAS))}")
    elif encabezados != COLUMNAS:
        raise ConfigurationError(
            f"La pestaña de Sheets debe tener las {len(COLUMNAS)} columnas actuales en el orden definido en COLUMNAS. "
            "Actualiza sus encabezados y columnas o configura una pestaña nueva con SHEETS_TAB_NAME."
        )

    return ws


def obtener_titulos_existentes_adb() -> set[str]:
    try:
        ws = _conectar_sheets()
        return {
            row[4].strip().lower()
            for row in ws.get_all_values()[1:]
            if len(row) > 14 and row[2].strip() == "ADB" and row[4].strip()
            and row[14].strip().lower() in {"alto", "medio", "bajo", "descartable"}
        }
    except ConfigurationError:
        raise
    except Exception:
        raise RuntimeError("No se pudo leer Google Sheets para comprobar duplicados. Intenta nuevamente.") from None


def obtener_ids_existentes() -> set[str]:
    try:
        ws = _conectar_sheets()
        return {
            row[0].strip() for row in ws.get_all_values()[1:]
            if len(row) > 14 and row[0].strip()
            and row[14].strip().lower() in {"alto", "medio", "bajo", "descartable"}
        }
    except ConfigurationError:
        raise
    except Exception:
        raise RuntimeError("No se pudo leer Google Sheets para comprobar duplicados. Intenta nuevamente.") from None


def escribir_en_sheets(filas: list[dict]) -> list[int]:

    if not get_settings().sheets_id:
        raise RuntimeError(
            "SHEETS_CONVOCATORIAS_ID no está configurado. "
            "Crea la hoja, copia su ID y agrégalo al .env."
        )
    if not filas:
        return []

    ws = _conectar_sheets()

 
    existentes = ws.get_all_values()
    por_id = {
        row[0].strip(): (number, row[14].strip().lower() if len(row) > 14 else "")
        for number, row in enumerate(existentes[1:], start=2) if row and row[0].strip()
    }

    _FECHAS = {"Fecha Publicación", "Deadline"}

    def _fmt_fecha(val: str) -> str:
        if val and len(val) == 10 and val[4] == "-":
            return f"{val[8:10]}-{val[5:7]}-{val[:4]}"
        return val

    rows_to_append = []
    numeros = []
    for fila in filas:
        row = []
        for col in COLUMNAS:
            val = str(fila.get(_CAMPO_A_CLAVE[col], "") or "")
            if col in _FECHAS:
                val = _fmt_fecha(val)
            row.append(val)
        item_id = row[0].strip()
        if not item_id:
            raise ValueError("La convocatoria necesita un ID para guardarse sin duplicados.")
        if item_id in por_id:
            number, encaje = por_id[item_id]
            if encaje not in {"alto", "medio", "bajo", "descartable"}:
                ws.update(values=[row], range_name=f"A{number}:P{number}", value_input_option="USER_ENTERED")
                por_id[item_id] = (number, row[14])
        else:
            number = len(existentes) + len(rows_to_append) + 1
            rows_to_append.append(row)
            por_id[item_id] = (number, row[14])
        numeros.append(number)

    if rows_to_append:
        ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")

    return numeros
