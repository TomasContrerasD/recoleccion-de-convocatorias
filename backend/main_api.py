"""FastAPI entry point for the banking consulting opportunities service."""

import asyncio
from secrets import compare_digest

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from config import ConfigurationError, get_settings
from servicios.recolector_de_convocatorias.email_sender import (
    enviar_resumen_convocatorias,
)
from servicios.recolector_de_convocatorias.orchestrator import (
    ejecutar_convocatorias,
    ejecutar_convocatorias_auto,
)

app = FastAPI(title="API del Recolector de Convocatorias")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "Recolector de convocatorias disponible"}


class ConvocatoriasRequest(BaseModel):
    ids: list[str] | None = None  # None = ejecutar todas las instituciones activas


@app.post("/api/convocatorias/run")
async def api_convocatorias_run(datos: ConvocatoriasRequest):
    def gen():
        ejecucion = ejecutar_convocatorias(datos.ids)
        while True:
            try:
                msg = next(ejecucion)
            except StopIteration as resultado:
                guardadas = resultado.value or []
                break
            except (ConfigurationError, RuntimeError) as error:
                yield "".join(f"data: {line}\n" for line in f"Error: {error}".split("\n")) + "\n"
                return
            # Prefix every line so multiline progress messages remain valid SSE.
            yield "".join(f"data: {line}\n" for line in str(msg).split("\n")) + "\n"

        settings = get_settings()
        if not settings.notify_email:
            return
        if not settings.gmail_user or not settings.gmail_app_password:
            yield "data: AVISO: Resumen por correo omitido: configura GMAIL_USER y GMAIL_APP_PASSWORD.\n\n"
            return

        yield "data: Correo: Enviando resumen de la ejecución...\n\n"
        try:
            enviar_resumen_convocatorias(guardadas, settings.notify_email)
        except Exception:
            yield "data: AVISO: No se pudo enviar el resumen por correo. Los resultados guardados se conservan.\n\n"
        else:
            yield "data: Correo: Resumen enviado.\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/convocatorias/auto")
async def api_convocatorias_auto(request: Request, datos: ConvocatoriasRequest | None = None):
    """Optional scheduled execution. Configure the schedule outside the application."""
    settings = get_settings()
    if not settings.enable_automation:
        raise HTTPException(status_code=404, detail="La automatización está desactivada.")
    secret = settings.scheduler_secret
    if not secret.strip():
        raise HTTPException(status_code=503, detail="La automatización requiere SCHEDULER_SECRET.")
    supplied = request.headers.get("X-Scheduler-Secret", "")
    if not compare_digest(secret.encode("utf-8"), supplied.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        resultado = await asyncio.to_thread(ejecutar_convocatorias_auto, datos.ids if datos else None)
    except ConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except Exception:
        raise HTTPException(status_code=502, detail="La ejecución falló. Revisa la configuración y las fuentes.") from None

    guardadas = resultado["guardadas"]
    total = resultado["total"]

    correo = "desactivado"
    if settings.notify_email and not guardadas:
        correo = "sin_novedades"
    elif settings.notify_email and (not settings.gmail_user or not settings.gmail_app_password):
        correo = "sin_configurar"
    elif settings.notify_email:
        try:
            await asyncio.to_thread(enviar_resumen_convocatorias, guardadas, settings.notify_email)
            correo = "enviado"
        except Exception:
            correo = "fallido"

    return JSONResponse(status_code=502 if resultado["errores"] else 200, content={
        "total_nuevas": total,
        "errores": resultado["errores"],
        "correo": correo,
        "mensaje": f"{total} convocatoria(s) nueva(s) detectada(s).",
    })
