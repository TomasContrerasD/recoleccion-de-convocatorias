from typing import Literal

from pydantic import BaseModel, ConfigDict
from config import get_settings
from .ia import obtener_cliente

_CONTEXTO_EMPRESA = """
EJEMPLO FICTICIO PARA DEMOSTRACIÓN: la empresa minera del ejemplo se denomina BHP.
La descripción, capacidades y prioridades siguientes son inventadas para probar
el proyecto; no representan información oficial ni compromisos de BHP real.

En este escenario, la empresa desarrolla proyectos de cobre y minerales críticos
en América Latina. Cuenta con equipos de ingeniería, evaluación económica,
innovación y sostenibilidad, y busca alianzas para mejorar sus operaciones.

Sus intereses hipotéticos son eficiencia energética, energías renovables, agua,
descarbonización, automatización, seguridad operacional, infraestructura logística,
economía circular, desarrollo de proveedores y relaciones con comunidades.

Evalúa convocatorias de organismos internacionales para detectar proyectos de
cooperación, inversión, innovación y asistencia técnica relacionados con minería.
Puede aportar conocimiento técnico, participar en pilotos o colaborar con socios
especializados. No asumas que cumple requisitos de consultora o contratista.

Prioriza oportunidades con una relación concreta con estos intereses. Distingue
participación directa, colaboración y señales de mercado, sin inventar elegibilidad,
experiencia, certificaciones o socios.
"""

_PROMPT_TEMPLATE = """Evalúa el encaje de esta convocatoria para la empresa descrita en el contexto.

CONVOCATORIA:
Institución: {institucion}
Título: {titulo}
Proyecto: {proyecto}
País: {pais}
Tipo de Aviso: {tipo_aviso}
Idioma: {idioma}
Deadline: {deadline}

DESCRIPCIÓN COMPLETA:
{texto_detalle}

CONTEXTO DE LA EMPRESA:
{contexto}

Devuelve únicamente {{"encaje": "..."}}, sin explicaciones.
Valores permitidos: "alto", "medio", "bajo", "descartable"."""


class _Clasificacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    encaje: Literal["alto", "medio", "bajo", "descartable"]


_FALLBACK = {"encaje": "sin_clasificar"}


def clasificar_convocatoria(aviso: dict) -> dict:
    texto = aviso.get("texto_detalle") or aviso.get("titulo", "")

    prompt = _PROMPT_TEMPLATE.format(
        institucion=aviso.get("institucion", ""),
        titulo=aviso.get("titulo", ""),
        proyecto=aviso.get("proyecto", ""),
        pais=aviso.get("pais", ""),
        tipo_aviso=aviso.get("tipo_aviso", ""),
        idioma=aviso.get("idioma", ""),
        deadline=aviso.get("deadline", ""),
        texto_detalle=texto,
        contexto=_CONTEXTO_EMPRESA,
    )

    try:
        respuesta = obtener_cliente().responses.parse(
            model=get_settings().openai_model,
            input=prompt,
            text_format=_Clasificacion,
            store=False,
        )
        if respuesta.status != "completed" or respuesta.output_parsed is None:
            return dict(_FALLBACK)
        return respuesta.output_parsed.model_dump()
    except Exception:
        return dict(_FALLBACK)
