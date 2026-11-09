import smtplib
from html import escape
from config import get_settings
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlsplit


_MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _fecha_ejecucion_es() -> str:
    hoy = date.today()
    return f"{hoy.day} de {_MESES_ES[hoy.month]} de {hoy.year}"


def _enlace_html(url: str, etiqueta: str = "Ver →") -> str:
    url = str(url or "").strip()
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "—"
    except ValueError:
        return "—"
    return f'<a href="{escape(url, quote=True)}" style="color:#1a73e8">{escape(etiqueta)}</a>'


def enviar_resumen_convocatorias(guardadas: list[dict], destinatario: str) -> None:
    """
    Send an HTML email to destinatario summarising newly found opportunities.
    Only items with encaje == "alto" appear in the table.
    Uses GMAIL_USER + GMAIL_APP_PASSWORD from environment.
    """
    settings = get_settings()
    gmail_user = settings.gmail_user
    gmail_password = settings.gmail_app_password

    if not gmail_user or not gmail_password or not destinatario:
        return

    total = len(guardadas)
    altas = [i for i in guardadas if (i.get("encaje") or "").lower() == "alto"]
    n_altas = len(altas)
    fecha_ejecucion = _fecha_ejecucion_es()

    subject = f"Resumen de la ejecución de convocatorias - {fecha_ejecucion}"

    rows_html = ""
    for item in altas:
        institucion = escape(str(item.get("institucion") or "—"))
        proyecto = escape(str(item.get("proyecto") or item.get("titulo") or "—")[:120])
        encaje = escape(str(item.get("encaje") or "—"))
        _d = str(item.get("deadline") or "")
        deadline = f"{_d[8:10]}-{_d[5:7]}-{_d[:4]}" if len(_d) == 10 and _d[4] == "-" else (_d or "—")
        deadline = escape(deadline)
        fila_num = item.get("_fila_sheets")
        ubicacion = escape(f"Fila {fila_num}") if fila_num else "—"

        link_aviso_html = _enlace_html(item.get("link", ""))
        link_proy_html = _enlace_html(item.get("link_proyecto", ""))

        rows_html += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;white-space:nowrap">{institucion}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee">{proyecto}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center">{link_aviso_html}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center">{link_proy_html}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;font-weight:bold;color:#16a34a">{encaje}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;white-space:nowrap">{deadline}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;color:#6b7280;white-space:nowrap">{ubicacion}</td>
        </tr>"""

    tabla_html = f"""
    <table style="border-collapse:collapse;width:100%;font-size:13px;margin-top:16px">
      <thead>
        <tr style="background:#F0982A;color:#fff">
          <th style="padding:10px 12px;text-align:left">Institución</th>
          <th style="padding:10px 12px;text-align:left">Proyecto</th>
          <th style="padding:10px 12px;text-align:center">Link Aviso</th>
          <th style="padding:10px 12px;text-align:center">Link Proyecto</th>
          <th style="padding:10px 12px;text-align:center">Encaje para la empresa</th>
          <th style="padding:10px 12px;text-align:center">Deadline (dd-mm-yyyy)</th>
          <th style="padding:10px 12px;text-align:center">Ubicación en Google Sheets</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>""" if altas else "<p style='color:#6b7280'>No se encontraron avisos de prioridad alta en esta ejecución.</p>"

    links_html = ""
    for label, url in (
        ("Detalle en Google Sheets", settings.sheets_url),
        ("Abrir la plataforma", settings.portal_url),
    ):
        if url:
            links_html += f'<p>{_enlace_html(url, label)}</p>'

    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;font-size:14px;color:#333;margin:0;padding:28px;max-width:900px">
      <p>Hola,</p>
      <p>
        Este correo resume las convocatorias de instituciones financieras internacionales
        recopiladas en esta ejecución.
      </p>
      <p>
        En la ejecución del <strong>{fecha_ejecucion}</strong> se guardaron <strong>{total} aviso(s) nuevo(s)</strong>,
        de los que <strong>{n_altas}</strong> son de encaje alto y se listan en la tabla a continuación:
      </p>

      <p style="font-size:12px;color:#6b7280;background:#f9f9f9;border-left:3px solid #F0982A;padding:8px 12px;margin-bottom:8px">
        <strong>Nota IDB (BEO corporativo):</strong> Si al hacer click en un link de IDB (BEO corporativo) aparece "You are not authorized", cierra esa pestaña,
        ingresa a <a href="https://beo-procurement.iadb.org/en/user/login" style="color:#1a73e8">https://beo-procurement.iadb.org/en/user/login</a>,
        selecciona <strong>"Consulting Firms"</strong> e ingresa con tu propia cuenta.
      </p>

      {tabla_html}

      {links_html}

      <p style="margin-top:32px;color:#9ca3af;font-size:11px;border-top:1px solid #e5e7eb;padding-top:12px">
        — Recolector de convocatorias · Resumen de la ejecución
      </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = destinatario
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, destinatario, msg.as_string())
