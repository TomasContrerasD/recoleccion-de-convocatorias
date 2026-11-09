# Automatización opcional en Google Cloud

El proyecto funciona manualmente en tu computador sin Cloud Run ni Cloud Scheduler.
La automatización está desactivada por defecto (`ENABLE_AUTOMATION=false`). Clonar
el repositorio no crea recursos ni modifica trabajos que ya existan en tu cuenta.
Esta guía prepara un backend privado para ejecución programada, no una web pública.

## 1. Preparar tu instalación

- Comprueba primero el flujo manual con tus propias credenciales.
- Usa una pestaña con las 16 columnas actuales de `sheets_writer.py`. Si existe una
  pestaña con otro esquema, actualiza sus columnas o configura otra pestaña.
- Elige las fuentes en `backend/servicios/recolector_de_convocatorias/instituciones.json`.
  BEO necesita sus propias credenciales; desactívalo si no tienes cuenta.
- Los scrapers AIIB, EBRD y EDCF están inactivos y fuera del registro del orquestador.
- Instala e inicia sesión en la CLI de Google Cloud con tu propia cuenta.
- Crea o selecciona tu proyecto y habilita facturación y las APIs de Cloud Run,
  Cloud Build, Artifact Registry, Secret Manager, Cloud Scheduler, Sheets y Drive.
  La facturación de OpenAI se configura aparte en tu cuenta de OpenAI.

Referencia: [desplegar desde código fuente](https://docs.cloud.google.com/run/docs/deploying-source-code).
Los permisos de compilación y despliegue dependen de tu proyecto; sigue los
requisitos de esa guía si tu cuenta no tiene permisos para crear el servicio.

## 2. Crear identidades y secretos

Crea una cuenta de servicio ejecutora para Cloud Run y otra invocadora para
Scheduler. No necesitan ser la misma cuenta que accede a Sheets.

En Secret Manager, crea estos secretos con tus propios valores:

| Nombre de ejemplo | Contenido | Variable del backend |
| --- | --- | --- |
| `openai-api-key` | Tu clave de OpenAI | `OPENAI_API_KEY` |
| `google-sheets-json` | El JSON completo de tu cuenta de servicio de Sheets | `GOOGLE_CREDENTIALS_JSON` |
| `scheduler-secret` | Una cadena aleatoria privada, generada para esta instalación | `SCHEDULER_SECRET` |
| `gmail-app-password` (opcional) | Tu contraseña de aplicación de Gmail | `GMAIL_APP_PASSWORD` |

Genera el secreto del programador con un generador de contraseñas seguras y
guárdalo de forma privada. Necesitarás ese mismo valor en la cabecera del trabajo
de Scheduler. No lo publiques en archivos, comandos compartidos, capturas o videos.

Comparte la hoja con el `client_email` del JSON de Sheets como **Editor**. El código
actual autentica Sheets con ese JSON; asignar una identidad a Cloud Run no sustituye
por sí solo esa credencial. Concede a la cuenta ejecutora de Cloud Run el rol
`Secret Manager Secret Accessor` sobre los secretos que vaya a utilizar.

Referencia: [secretos en Cloud Run](https://docs.cloud.google.com/run/docs/configuring/services/secrets).

## 3. Desplegar el backend privado

Desde la raíz del repositorio, reemplaza los identificadores de ejemplo y ejecuta
este comando solamente cuando quieras crear recursos en tu proyecto. Las versiones
`:1` deben corresponder a versiones existentes de tus secretos:

```text
gcloud run deploy recolector-convocatorias --source backend --project MI_PROYECTO --region MI_REGION --service-account EJECUTOR@MI_PROYECTO.iam.gserviceaccount.com --no-allow-unauthenticated --concurrency 1 --max-instances 1 --timeout 1800 --set-env-vars ENABLE_AUTOMATION=true,OPENAI_MODEL=gpt-6-luna,SHEETS_CONVOCATORIAS_ID=ID_DE_MI_HOJA,SHEETS_TAB_NAME=Convocatorias,PORTAL_URL= --set-secrets OPENAI_API_KEY=openai-api-key:1,GOOGLE_CREDENTIALS_JSON=google-sheets-json:1,SCHEDULER_SECRET=scheduler-secret:1
```

`backend/.gcloudignore` excluye los secretos y el entorno virtual de la subida de
código. `.dockerignore` los excluye de la imagen. Mantén las credenciales en los
secretos configurados; no copies tu `.env` ni `credentials.json` al contenedor.

En **Cloud Run → servicio → Variables y secretos**, puedes agregar:

- `GMAIL_USER` y `NOTIFY_EMAIL`, y la referencia de `GMAIL_APP_PASSWORD` a su secreto.
- `BEO_EMAIL` y una referencia secreta para `BEO_PASSWORD` si activas BEO.
- `PORTAL_URL` si tienes una página publicada; vacío omite ese enlace del correo.
- `CORS_ORIGINS` solo si vas a configurar otro cliente autorizado para este backend.

El despliegue inicia Uvicorn con un proceso. Conserva una instancia y concurrencia
uno para este flujo secuencial.

El frontend local debe seguir apuntando a tu backend local. Publicar también el
frontend y conectarlo al backend privado requiere configurar autenticación entre
ambos; el login del frontend no concede permisos IAM sobre Cloud Run.

## 4. Crear el trabajo de Cloud Scheduler

Concede a la cuenta invocadora de Scheduler el rol **Cloud Run Invoker** sobre el
servicio desplegado. Después crea un trabajo HTTP en la consola:

| Opción | Valor |
| --- | --- |
| Nombre | Un nombre propio, por ejemplo `recolectar-convocatorias` |
| Región | Una región compatible de tu elección |
| Frecuencia | La que tú elijas; `0 9 * * 1-5` es un ejemplo de lunes a viernes a las 09:00 |
| Zona horaria | Tu zona IANA, por ejemplo `America/Santiago` |
| URL | `https://URL_DE_TU_SERVICIO/api/convocatorias/auto` |
| Método | `POST` |
| Cabecera | `Content-Type: application/json` |
| Cabecera privada adicional | `X-Scheduler-Secret: TU_SECRETO` |
| Cuerpo inicial | `{"ids":["rfxnow"]}` para probar una sola fuente; `{}` ejecuta todas las activas |
| Autenticación | OIDC con la cuenta invocadora |
| Audience | URL base de Cloud Run, sin `/api/convocatorias/auto` |
| Deadline | Hasta 30 minutos para el destino HTTP |
| Máximo de reintentos | Empieza con `0`; ajusta tras medir el tiempo y revisar los resultados |

El horario no existe dentro del código Python: lo establece este trabajo.
Un trabajo anterior no cambia al editar tu copia local del proyecto.

Referencias: [Scheduler con Cloud Run privado](https://docs.cloud.google.com/run/docs/triggering/using-scheduler),
[opciones del trabajo HTTP](https://docs.cloud.google.com/sdk/gcloud/reference/scheduler/jobs/create/http).

## 5. Verificar el resultado y los reintentos

Ejecutar el trabajo manualmente desde la consola es una ejecución **real**: hace
scraping, consume OpenAI y escribe en Sheets. Revisa antes las fuentes y credenciales.

- `404`: automatización desactivada.
- `403`: secreto de cabecera incorrecto o acceso rechazado por IAM.
- `422`: cuerpo JSON incompatible; `ids` debe ser una lista de strings.
- `502`: falló una fuente, una clasificación o una escritura; revisa `errores`.
- `503`: configuración necesaria ausente o inválida.
- `200`: terminó la recolección sin errores. El campo `correo` informa `enviado`,
  `fallido`, `sin_novedades`, `sin_configurar` o `desactivado`.

Un error de correo no provoca por sí solo un reintento HTTP: Sheets puede haberse
guardado correctamente y SMTP puede haber aceptado un mensaje antes de un corte
de conexión. Revisa `correo` y los registros; no se garantiza entrega exactamente
una vez ni se mantiene una cola persistente de notificaciones.

Los IDs repetidos de un lote se descartan. Si falla la lectura de duplicados se
detiene el proceso, y una clasificación fallida no se guarda como procesada. Los
registros antiguos sin clasificación válida se pueden reclasificar actualizando
su misma fila. Un ID ya clasificado no se vuelve a agregar al guardar.

Scheduler puede entregar más de una vez incluso con reintentos configurados en
cero. Estas defensas están pensadas para ejecuciones **secuenciales**. Sheets no
proporciona aquí un bloqueo distribuido ni una operación atómica de unicidad:
no ejecutes varias instalaciones contra la misma pestaña simultáneamente. Para
paralelismo, añade un almacenamiento con transacciones y una estrategia de bloqueo.
Si el proceso supera el deadline, divide las fuentes en trabajos separados que
no se solapen, o adapta la ejecución a Cloud Run Jobs.

Referencia: [semántica de ejecución de Scheduler](https://docs.cloud.google.com/scheduler/docs/overview).

## 6. Desactivar

Pausa el trabajo en Cloud Scheduler y establece `ENABLE_AUTOMATION=false` en el
servicio de Cloud Run. Cambiar solamente `backend/.env` afecta tu instalación
local, no los recursos ya desplegados. La ejecución manual local sigue disponible.
