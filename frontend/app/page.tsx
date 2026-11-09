"use client";

import { useState, useRef, useEffect } from "react";
import { consumeSseStream } from "./lib/sse";

const instituciones = [
  {
    id: "wbg",
    nombre: "WBG — World Bank Group (Proyectos)",
    pais: "Global",
    url: "https://projects.worldbank.org/en/projects-operations/opportunities",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal de procurement de proyectos financiados por WBG. El consultor es contratado por el gobierno receptor del préstamo, no por WBG directamente.",
      "Recopila avisos con deadline activo (≥ hoy) sin importar cuándo fueron publicados.",
      "Filtros: Tipo = Consultant Services · Sectores = Banking Institutions, Capital Markets, Central Government, Mining · Avisos = Invitation for Bids, Invitation for Prequalification, Request for Expression of Interest.",
    ],
  },
  {
    id: "rfxnow",
    nombre: "WBG (Corporativo)",
    pais: "Global",
    url: "https://wbgeprocure-rfxnow.worldbank.org/rfxnow/public/advertisement/index.html",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal RFx Now (WBGeProcure) — procurement corporativo del WBG Group completo. El cliente es WBG/IFC directamente (no un gobierno). Contratan consultoras para su propio trabajo: estudios, advisory services, evaluaciones internas.",
      "Recopila todos los avisos activos publicados en el portal al momento de la ejecución.",
      "Incluye convocatorias de IFC, MIGA, GIF, GWSP, GFF y otras entidades del grupo.",
    ],
  },
  {
    id: "caf",
    nombre: "CAF — Development Bank of Latin America and the Caribbean",
    pais: "América Latina y el Caribe",
    url: "https://www.caf.com/en/work-with-us/calls/",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal de Calls del CAF — procurement corporativo del banco. El cliente es CAF directamente. Contratan consultoras para estudios, advisory y asistencia técnica en América Latina y el Caribe.",
      "Sin API JSON: scraping de HTML con BeautifulSoup. Más frágil que las fuentes con API, pero la estructura del sitio es estable.",
      "Incluye todos los tipos de convocatoria (consultoría, bienes, concursos). OpenAI filtra y clasifica por relevancia.",
    ],
  },
  {
    id: "beo",
    nombre: "IDB — Inter-American Development Bank (Corporativo)",
    pais: "América Latina y el Caribe",
    url: "https://beo-procurement.iadb.org/en/home",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal BEO del BID — procurement corporativo del banco. El cliente es el BID directamente (no un gobierno). Contratan consultoras para su propio trabajo: advisory, estudios, evaluaciones internas.",
      "Recopila todos los REOIs activos. Requiere login con cuenta de Consulting Firm registrada en el portal.",
      "Análogo a RFx Now del WBG. Sin acceso al detalle completo del aviso (requiere IDB Staff), pero el título y sector son suficientes para clasificación.",
    ],
  },
  {
    id: "idb",
    nombre: "IDB (Proyectos)",
    pais: "América Latina y el Caribe",
    url: "https://bidfortheamericas.connectamericas.com/es/licitaciones",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal ConnectAmericas del BID. Contratos financiados por el BID en proyectos de América Latina y el Caribe. El consultor es contratado por el gobierno receptor del préstamo, no por el BID directamente.",
      "Recopila avisos con deadline activo (≥ hoy) sin importar cuándo fueron publicados.",
      "Incluye todos los tipos de aviso (consultoría, bienes, obras). OpenAI filtra y clasifica por relevancia para servicios de consultoría.",
    ],
  },
  {
    id: "ungm",
    nombre: "UNGM — United Nations Global Marketplace + (60+ agencias ONU)",
    pais: "Global",
    url: "https://www.ungm.org/Public/Notice",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal público de procurement de toda la familia ONU. POST /Public/Notice/Search con JSON — sin autenticación requerida. Cubre UNDP, UNOPS, UNICEF, WFP, FAO, UNFPA y 54+ agencias más.",
      "Recopila avisos con deadline activo (≥ hoy): filtro IsActive=True + DeadlineFrom=hoy en el payload.",
      "Filtros de tipo aplicados: Solicitud de propuesta (RFP) · Solicitud de manifestación de interés (EOI) · Convocatoria de propuestas de apoyo económico (CP-QB-FBS).",
      "Las convocatorias de PNUD/UNDP que aparezcan también en el scraper de UNDP son deduplicadas automáticamente por Ref No en Google Sheets.",
    ],
  },
  {
    id: "undp",
    nombre: "UNDP — United Nations Development Programme",
    pais: "Global",
    url: "https://procurement-notices.undp.org/",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal público de procurement de UNDP. Todos los avisos activos se cargan en una sola página (filtrado client-side, sin paginación server-side). Sin API — HTML scraping con BeautifulSoup.",
      "Recopila avisos con deadline activo (≥ hoy): el portal de UNDP solo muestra convocatorias abiertas al momento de la consulta.",
      "Filtros de proceso aplicados: RFP (Request for Proposal) · EOI (Expression of Interest) · CP-QB-FBS (Call for Proposal – Quality Based Fixed Budget). Se descartan ITB, RFQ, IC, ITP, RFI y otros tipos no relevantes para firmas consultoras.",
      "Para cada aviso filtrado se obtiene la página de detalle con descripción completa y email de contacto, lo que permite una clasificación más precisa por parte de OpenAI.",
    ],
  },
  {
    id: "eib",
    nombre: "EIB — European Investment Bank",
    pais: "Global (foco Europa + países socios)",
    url: "https://www.eib.org/en/about/procurement/all/index.htm",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: API REST pública del EIB — sin autenticación requerida. Incluye asistencia técnica, estudios, advisory y proyectos fuera de la UE (non-EU).",
      "Cobertura global con foco en Europa, pero incluye proyectos en países socios de América Latina (Brasil, Ecuador, entre otros). OpenAI filtra por relevancia.",
      "137+ avisos activos en promedio. Categorías principales: TA operations, Studies, Advisory.",
    ],
  },
  {
    id: "jbic",
    nombre: "JBIC — Japan Bank for International Cooperation",
    pais: "Japón / Global",
    url: "https://www.jbic.go.jp/ja/info.html",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal de procurement corporativo del JBIC — banco japonés de cooperación internacional. Solo disponible en japonés; la versión en inglés no incluye convocatorias.",
      "Sin API — scraping HTML de tablas server-rendered. Tres secciones: licitación general (一般競争入札), convocatoria pública (公募) y concurso de planificación (企画競争).",
      "~15 oportunidades activas simultáneas en promedio. Títulos traducidos al español automáticamente vía OpenAI antes de ingresar al pipeline de clasificación.",
    ],
  },
  {
    id: "jogmec",
    nombre: "JOGMEC — Japan Oil, Gas and Metals National Corporation",
    pais: "Japón / Global",
    url: "https://www.jogmec.go.jp/english/bid/search.php",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal de licitaciones corporativas del JOGMEC en inglés. Sin API — scraping HTML de tabla server-rendered.",
      "Sin columna de deadline ni en el listado ni en los avisos individuales. Solo se scrapea la primera página; la deduplicación por ID en Sheets evita reprocesar avisos anteriores.",
    ],
  },
  {
    id: "cidca",
    nombre: "CIDCA — China International Development Cooperation Agency",
    pais: "Global (foco Belt and Road + América Latina)",
    url: "https://en.cidca.gov.cn/",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "DESCARTADA — No es un portal de procurement. CIDCA es una agencia de política y ejecución de ayuda exterior china; sus contratos van directamente a empresas estatales chinas sin proceso competitivo público abierto.",
      "El sitio tiene geo-restricciones (inaccesible desde fuera de China), lo que hace inviable cualquier scraping automatizado.",
    ],
  },
  {
    id: "exim",
    nombre: "EXIM Bank — Export-Import Bank of the United States",
    pais: "Global (financiamiento a exportadores de EE.UU.)",
    url: "https://www.exim.gov/",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "DESCARTADA — No es una fuente de contratos de consultoría. EXIM es una agencia de crédito a exportaciones: financia a empresas estadounidenses que exportan, no contrata consultoras para proyectos de desarrollo.",
      "Sus contratos internos se publican en SAM.gov (ver entrada SAM.gov) y están restringidos a entidades registradas en EE.UU.",
    ],
  },
  {
    id: "samgov",
    nombre: "SAM.gov — System for Award Management (EE.UU.)",
    pais: "EE.UU. (contratos federales)",
    url: "https://sam.gov/",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "API interna sin autenticación confirmada (sam.gov/api/prod/sgs/v1/search). USAID filtrada por organization_id=100148640. Solo 4 resultados totales, todos 'Special Notice', el más reciente de agosto 2024.",
      "USAID fue efectivamente desmantelada en 2025 bajo la administración Trump — sin Solicitations, Sources Sought ni Presolicitations activas. Fuente técnicamente viable pero sin actividad contractual en la actualidad.",
    ],
  },
  {
    id: "jica",
    nombre: "JICA — Japan International Cooperation Agency",
    pais: "Global (foco Asia + América Latina)",
    url: "https://www.jica.go.jp/english/index.html",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "DESCARTADA — No se encontraron convocatorias públicas scrapeables. El sitio principal es informacional y las oficinas de país (ej. JICA Chile) solo publican noticias y datos de contacto, sin listado de oportunidades abiertas.",
      "No existe un portal centralizado de procurement en jica.go.jp. Las oportunidades estarían repartidas por subpáginas de cada oficina de país, sin estructura uniforme ni API.",
    ],
  },
  {
    id: "unido",
    nombre: "UNIDO — United Nations Industrial Development Organization",
    pais: "Global",
    url: "https://www.unido.org/get-involved/procurement/procurement-opportunities",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "DESCARTADA como fuente independiente — UNIDO está registrada en UNGM y sus convocatorias de tipo RFP, EOI y CP-QB-FBS ya son capturadas por el scraper de UNGM.",
    ],
  },
  {
    id: "afdb",
    nombre: "AfDB — African Development Bank",
    pais: "África",
    url: "https://www.afdb.org/en/about-us/corporate-procurement/procurement-notices/current-solicitations",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal de procurement corporativo del AfDB — banco de desarrollo de África, sede en Abiyán (Costa de Marfil). Foco geográfico: continente africano.",
      "Incluido por decisión estratégica: las convocatorias de consultoría sectorial (minería, energía, infraestructura) son relevantes para el perfil de la empresa independientemente de la región.",
      "Datos bien estructurados. OpenAI filtra por tipo de consultoría relevante.",
    ],
  },
  {
    id: "adb",
    nombre: "ADB — Asian Development Bank",
    pais: "Asia y el Pacífico",
    url: "https://selfservice.adb.org/OA_HTML/OA.jsp?OAFunc=XXCRS_CSRN_HOME_PAGE",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: true,
    comentarios: [
      "Fuente: Portal CSRN del ADB — banco de desarrollo de Asia y el Pacífico. 166+ oportunidades activas en promedio (Firm + Individual).",
      "Incluido por decisión estratégica: aunque opera en Asia (Bangladesh, Filipinas, Pakistán, China, Nepal), las convocatorias de consultoría en minería, energía y recursos naturales son relevantes para el perfil de la empresa.",
      "Portal Oracle OAF (server-rendered, sin API). Los filtros de sector/país requieren JavaScript; se scrapean todos los avisos activos y OpenAI filtra por relevancia. Paginación de 25 items/página via POST de formulario OAF — si la navegación falla, se captura la primera página en cada ejecución diaria.",
    ],
  },
  {
    id: "eiti",
    nombre: "EITI — Extractive Industries Transparency Initiative",
    pais: "Global",
    url: "https://eiti.org/call-tenders",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "DESCARTADA — No es una fuente de contratos de consultoría. Las 'convocatorias' de EITI son procesos de validación de países (Consultations) donde se pide feedback de partes interesadas, no licitaciones con adjudicatario y pago.",
      "EITI es una iniciativa de gobernanza/transparencia, no un banco de desarrollo que contrate consultoras.",
    ],
  },
  {
    id: "isa",
    nombre: "ISA — International Seabed Authority",
    pais: "Global (fondo marino internacional)",
    url: "https://isa.org.jm/category/call-for-proposals/",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "DESCARTADA — Foco temático incompatible. ISA es el organismo de la ONU para la minería del fondo marino (nódulos polimetálicos, sulfuros hidrotermales). Sus consultorías requieren oceanógrafos, biólogos marinos y expertos en derecho del mar — no asesores de mercado de cobre, oro o hierro en América Latina.",
      "Actividad casi nula: la última propuesta publicada data de 2024.",
    ],
  },
  {
    id: "idb_invest",
    nombre: "IDB Invest (brazo sector privado del BID)",
    pais: "Global",
    url: "https://idbinvest.org/en/idb-invest-procurement",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "1 sola oportunidad activa al momento de evaluación (RFI de IT Services interno). Sin estructura de datos: solo PDFs para descargar, sin campos parseables (título, deadline, país). Sin API, sin paginación, sin filtros.",
      "El portal lo dice explícitamente: \"Procurement opportunities with IDB Invest clients are not listed below and must be consulted directly with the respective client.\"",
      "OJO: Las oportunidades del BID ya están cubiertas por dos fuentes más ricas: BEO (procurement corporativo del banco) y ConnectAmericas (proyectos financiados en la región).",
    ],
  },
  {
    id: "edc_merx",
    nombre: "EDC / MERX — Export Development Canada",
    pais: "Canadá",
    url: "https://www.merx.com/public/solicitations/open",
    fecha_agregada: "08-11-2026",
    ultima_actualizacion: "08-11-2026",
    activa: false,
    comentarios: [
      "Incompatibilidad de producto: EDC es una agencia de crédito a exportaciones (financia a empresas canadienses que exportan), no un banco de desarrollo que comisione consultoría en América Latina. Mismo perfil que EXIM.",
      "EDC no publica licitaciones propias — redirige a MERX.com, plataforma de procurement doméstico canadiense con 1.500–2.500 tenders activos de municipalidades, ministerios, universidades y constructoras canadienses.",
      "La categoría 'Natural Resources Services' en MERX corresponde a gestión forestal, pesca, parques nacionales e inspección de oleoductos domésticos — no consultoría de mercados mineros en América Latina.",
      "Relación señal/ruido inviable: filtrar 1.500+ avisos por run con OpenAI para encontrar 0 oportunidades relevantes tiene un costo de API real y retorno nulo.",
    ],
  },
];

const SHEET_URL = process.env.NEXT_PUBLIC_SHEETS_URL ?? "";

type Tab = "activas" | "no_vale" | "descartadas";

const TABS: { id: Tab; label: string }[] = [
  { id: "activas", label: "Activas" },
  { id: "no_vale", label: "Hay convocatorias, pero no valen la pena scrapear" },
  { id: "descartadas", label: "Instituciones analizadas pero descartadas" },
];

const TAB_IDS: Partial<Record<Tab, string[]>> = {
  no_vale: ["idb_invest", "edc_merx", "samgov"],
  descartadas: ["eiti", "isa", "unido", "jica", "cidca", "exim"],
};

function getTab(id: string): Tab {
  for (const [tab, ids] of Object.entries(TAB_IDS)) {
    if ((ids as string[]).includes(id)) return tab as Tab;
  }
  return "activas";
}

export default function ConvocatoriasBancariasPage() {
  const [seleccionadas, setSeleccionadas] = useState<string[]>([]);
  const [mensajes, setMensajes] = useState<string[]>([]);
  const [cargando, setCargando] = useState(false);
  const [tabActual, setTabActual] = useState<Tab>("activas");
  const consolaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (consolaRef.current) consolaRef.current.scrollTop = consolaRef.current.scrollHeight;
  }, [mensajes]);

  const institucionesVisibles = instituciones.filter(i => getTab(i.id) === tabActual);
  const activasParaEjecutar = institucionesVisibles.filter(i => i.activa !== false);

  const toggleSeleccion = (id: string) => {
    setSeleccionadas(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const toggleTodas = () => {
    setSeleccionadas(prev =>
      prev.length === activasParaEjecutar.length ? [] : activasParaEjecutar.map(i => i.id)
    );
  };

  const ejecutar = async (ids: string[]) => {
    if (ids.length === 0) return;
    setCargando(true);
    setMensajes([]);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const respuesta = await fetch(`${apiUrl.replace(/\/$/, "")}/api/convocatorias/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      });
      if (!respuesta.body) throw new Error("No hay conexión con el servidor.");
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      await consumeSseStream(respuesta.body, (message) => {
        setMensajes(prev => [...prev, message]);
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Error desconocido";
      setMensajes(prev => [...prev, `❌ Error: ${message}`]);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="app-page">
      <div className="app-container">
        {/* CABECERA */}
        <div className="mb-6 border-b-4 border-[#F0982A] pb-6">
          <h1
            className="text-[1.6rem] font-extrabold text-gray-900 mb-2"
            style={{ fontFamily: "var(--font-inter)", letterSpacing: "-0.01em" }}
          >
            Convocatorias a Consultorías de Instituciones Financieras Internacionales
          </h1>
        </div>

        {/* ENLACES RÁPIDOS */}
        <div className="mb-6">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
            Enlaces rápidos
          </p>
          <div className="flex flex-wrap gap-2 items-center">
            {SHEET_URL ? (
              <a
                href={SHEET_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="group inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-100 border border-gray-200 text-sm font-semibold text-gray-700 no-underline transition-all duration-200 hover:border-[#F0982A] hover:bg-orange-50 hover:text-[#b45309] cursor-pointer"
              >
                {/* Spreadsheet icon (green) */}
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-green-600 flex-shrink-0">
                  <path fillRule="evenodd" d="M.99 5.24A2.25 2.25 0 0 1 3.25 3h13.5A2.25 2.25 0 0 1 19 5.25l.01 9.5A2.25 2.25 0 0 1 16.76 17H3.26A2.25 2.25 0 0 1 1 14.74l-.01-9.5zm8.26 9.52v-.001l.006-.006-.001.007ZM9.74 14h6.01l.01-3.5H9.74v3.5zm0-5h6.011L15.75 5.5H9.74V9zm-1.5 5V9H2.25v5h5.99zm-5.99-6.5h5.99V5.5H2.25V7.5z" clipRule="evenodd" />
                </svg>
                Base de Datos de Convocatorias
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3 opacity-40 group-hover:opacity-80 flex-shrink-0 transition-opacity">
                  <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 0 0-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 0 0 .75-.75v-4a.75.75 0 0 1 1.5 0v4A2.25 2.25 0 0 1 12.75 17h-8.5A2.25 2.25 0 0 1 2 14.75v-8.5A2.25 2.25 0 0 1 4.25 4h5a.75.75 0 0 1 0 1.5h-5ZM10 2.75a.75.75 0 0 1 .75-.75h6.5a.75.75 0 0 1 .75.75v6.5a.75.75 0 0 1-1.5 0V4.56l-5.97 5.97a.75.75 0 0 1-1.06-1.06l5.97-5.97h-4.69a.75.75 0 0 1-.75-.75Z" clipRule="evenodd" />
                </svg>
              </a>
            ) : (
              <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-100 border border-gray-200 text-sm text-gray-400 italic">
                Google Sheets (pendiente de configurar)
              </span>
            )}
          </div>
          <div className="mt-4 flex gap-3 items-start px-4 py-3 rounded-r-lg border-l-4 border-[#F0982A]" style={{ background: "rgba(240,152,42,0.06)" }}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-[#b45309] flex-shrink-0 mt-0.5">
              <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-gray-600 leading-relaxed">Selecciona las instituciones y ejecuta la recopilación manualmente.</p>
          </div>
        </div>

        {/* CAJA: Tabla de instituciones */}
        <div className="app-card-static rounded-xl p-6 mb-8 bg-white">
          <h2 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
            <span
              className="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold text-white"
              style={{ background: "#F0982A" }}
            >1</span>
            Instituciones Monitoreadas
          </h2>

          {/* PESTAÑAS */}
          <div className="flex gap-2 mb-6 flex-wrap">
            {TABS.map(tab => {
              const count = instituciones.filter(i => getTab(i.id) === tab.id).length;
              const isActive = tabActual === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => { setTabActual(tab.id); setSeleccionadas([]); }}
                  className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                    tab.id === "activas"
                      ? isActive
                        ? "bg-green-600 text-white border border-green-700"
                        : "bg-green-50 text-black hover:bg-green-600 hover:text-white border border-green-200"
                      : isActive
                        ? "bg-red-600 text-white border border-red-700"
                        : "bg-red-50 text-black hover:bg-red-600 hover:text-white border border-red-200"
                  }`}
                >
                  {tab.label}
                  <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    isActive
                      ? "bg-white/20 text-white"
                      : tab.id === "activas"
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* TABLA */}
          <div className="rounded-xl border border-gray-200 overflow-hidden mb-6 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b-2 border-[#F0982A] text-gray-500 uppercase text-xs tracking-wider bg-gray-50">
                  {tabActual === "activas" && (
                    <th className="py-3 pl-4 pr-3 w-8" style={{ background: "#ffedd5" }}>
                      <input
                        type="checkbox"
                        checked={seleccionadas.length === activasParaEjecutar.length && activasParaEjecutar.length > 0}
                        onChange={toggleTodas}
                        className="accent-[#F0982A] w-4 h-4 cursor-pointer"
                      />
                    </th>
                  )}
                  <th className="py-3 px-4" style={{ background: tabActual === "activas" ? "#ffedd5" : "#fee2e2" }}>Institución</th>
                  <th className="py-3 px-4">País / Región</th>
                  <th className="py-3 px-4">Link</th>
                  <th className="py-3 px-4">Fecha Agregada</th>
                  <th className="py-3 px-4">Última Actualización</th>
                  <th className="py-3 px-4">Comentarios</th>
                </tr>
              </thead>
              <tbody>
                {institucionesVisibles.map((inst) => {
                  const descartada = inst.activa === false;
                  const esTabActivas = tabActual === "activas";
                  return (
                    <tr
                      key={inst.id}
                      className={`border-b border-gray-100 transition-colors ${
                        esTabActivas && descartada ? "cursor-default hover:bg-gray-50" :
                        esTabActivas ? "hover:bg-gray-50 cursor-pointer" :
                        "hover:bg-gray-50"
                      }`}
                      style={seleccionadas.includes(inst.id) ? { background: "rgba(240,152,42,0.07)", outline: "2px solid #F0982A", outlineOffset: "-1px" } : {}}
                      onClick={() => esTabActivas && !descartada && toggleSeleccion(inst.id)}
                    >
                      {esTabActivas && (
                        <td className="py-4 pl-4 pr-3" style={{ background: seleccionadas.includes(inst.id) ? "rgba(240,152,42,0.20)" : "#ffedd5" }} onClick={e => e.stopPropagation()}>
                          {descartada ? (
                            <span className="text-xs text-red-400 font-bold">✕</span>
                          ) : (
                            <input
                              type="checkbox"
                              checked={seleccionadas.includes(inst.id)}
                              onChange={() => toggleSeleccion(inst.id)}
                              className="accent-[#F0982A] w-4 h-4 cursor-pointer"
                            />
                          )}
                        </td>
                      )}
                      <td className="py-4 px-4 font-semibold" style={{ background: esTabActivas ? (seleccionadas.includes(inst.id) ? "rgba(240,152,42,0.20)" : "#ffedd5") : "#fee2e2" }}>
                        <span className="text-gray-900">{inst.nombre}</span>
                        {esTabActivas && descartada && (
                          <span className="ml-2 text-xs px-2 py-0.5 rounded font-normal" style={{ background: "rgba(220,38,38,0.08)", color: "#dc2626", border: "1px solid rgba(220,38,38,0.18)" }}>
                            Descartada
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-gray-900">{inst.pais}</td>
                      <td className="py-4 px-4" onClick={e => e.stopPropagation()}>
                        <a href={inst.url} target="_blank" rel="noopener noreferrer" className="text-sky-500 hover:text-sky-600 hover:underline transition-colors">
                          Ver sitio →
                        </a>
                      </td>
                      <td className="py-4 px-4 text-gray-900">{inst.fecha_agregada}</td>
                      <td className="py-4 px-4 text-gray-900">{inst.ultima_actualizacion ?? "—"}</td>
                      <td className="py-4 px-4 text-gray-700 text-xs">
                        {inst.comentarios.length > 0 ? (
                          <ul className="list-disc list-inside space-y-1">
                            {inst.comentarios.map((c, i) => <li key={i}>{c}</li>)}
                          </ul>
                        ) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          </div>

          {/* Botones de ejecución (solo pestaña activas) */}
          {tabActual === "activas" && (
            <div className="flex gap-4 flex-wrap">
              <button
                onClick={() => ejecutar(activasParaEjecutar.map(i => i.id))}
                disabled={cargando}
                className="inline-flex items-center gap-2 font-bold text-sm px-5 py-2.5 rounded-lg border border-gray-400 bg-gray-500 text-white cursor-pointer transition-all hover:bg-gray-600 disabled:opacity-45 disabled:cursor-not-allowed"
              >
                {cargando ? "Procesando..." : "▶ Ejecutar todas"}
              </button>
              <button
                onClick={() => ejecutar(seleccionadas)}
                disabled={cargando || seleccionadas.length === 0}
                className="inline-flex items-center gap-2 font-bold text-sm px-5 py-2.5 rounded-lg border border-blue-500 bg-blue-500 text-black cursor-pointer transition-all hover:bg-blue-600 hover:border-blue-600 disabled:opacity-45 disabled:cursor-not-allowed"
              >
                ▶ Ejecutar seleccionadas ({seleccionadas.length})
              </button>
            </div>
          )}

          {/* Consola SSE */}
          {mensajes.length > 0 && (
            <div className="app-console h-[300px]">
              <div className="app-console-bar">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="app-console-label">Registro de ejecución</span>
              </div>
              <div ref={consolaRef} className="p-4 font-mono text-xs overflow-y-auto space-y-1 flex-grow">
                {mensajes.map((msg, idx) => (
                  <div key={idx}>
                    <span className="text-gray-500 mr-3">[{new Date().toLocaleTimeString()}]</span>
                    <span className={
                      msg.includes("❌") ? "text-red-400" :
                      msg.includes("✅") ? "text-green-400" :
                      "text-gray-300"
                    }>
                      {msg}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
