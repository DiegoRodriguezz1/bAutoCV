# bAutoCV API

Base backend con FastAPI, estructura por capas y configuracion por ambientes.

## Estructura

```
app/
  api/
  controllers/
  core/
  db/
  entities/
  schemas/
  services/
main.py
.env.dev
.env.prod
.env.example
```

## Ambientes

- `.venv`: entorno virtual de Python (dependencias).
- `.env.*`: variables de configuracion de la app (credenciales, host, flags).

El proyecto carga automaticamente `.env.<APP_ENV>`.
Por defecto: `APP_ENV=dev`.

## Ejecutar

Simply:

Instalar dependencias (requerimients.txt)
python -m pip install fastapi uvicorn[standard] sqlalchemy asyncpg python-dotenv pydantic-settings rendercv[full]


Defaults to `APP_ENV=dev`. To use a different environment:

```bash
# Bash
export APP_ENV=dev
python -m uvicorn main:app --reload
```

## Swagger

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Endpoints Base

- `GET /` estado simple del servicio
- `GET /api/v1/health` estado de app y conexion DB

## Endpoints CV y RenderCV

- `POST /api/v1/cv/render` renderizar a PDF desde YAML estructurado o libre
- `POST /api/v1/cv/yaml` generar YAML de RenderCV sin renderizar PDF
- `GET /api/v1/cv/download/{filename}` descargar PDF generado

## Endpoints OCR (PDF -> Datos -> YAML)

- `POST /api/v1/ocr/extract-cv` extraer texto y datos estructurados desde PDF (con Gemini opcional)
- `POST /api/v1/ocr/extract-cv-preview` preview rapido usando regex (sin Gemini)

## Endpoints ESCO: Búsqueda Rápida y Flujo de Asistente

El API ofrece un flujo optimizado de ocupación → skills → descripción para llenar la sección de perfil del CV de manera automática desde ESCO.

### Ocupaciones

1. **Búsqueda rápida (autocomplete):**
   ```bash
   GET /api/v1/esco/occupations/suggest?text=desarrollador&language=es&limit=10
   ```
   Fast `suggest2` endpoint. Mejor para autocompletar mientras escribe el usuario.

2. **Búsqueda más exhaustiva:**
   ```bash
   GET /api/v1/esco/occupations/search?text=desarrollo software&language=es&limit=10
   ```
   Búsqueda de texto completo con más resultados.

### Seleccionar Ocupación y Cargar Skills

3. **Obtener ocupación + skills esenciales y opcionales:**
   ```bash
   GET /api/v1/esco/occupations/skills?occupation_uri=http://data.europa.eu/esco/occupation/...&language=es&limit=20
   ```
   Responde con la ocupación seleccionada + sus ~20 skills esenciales y ~20 opcionales.

### Generar Descripción Automática

4. **Construir resumen, highlights y fragmento YAML desde ESCO:**
   ```bash
   POST /api/v1/esco/occupations/description-assistant
   Content-Type: application/json

   {
     "occupation_uri": "http://data.europa.eu/esco/occupation/...",
     "selected_skill_uris": [
       "http://data.europa.eu/esco/skill/...",
       "http://data.europa.eu/esco/skill/..."
     ],
     "language": "es",
     "additional_context": ["5 años de experiencia", "trabajo remoto"],
     "skill_limit": 20
   }
   ```
   Retorna:
   - `suggested_headline`: titular profesional
   - `suggested_summary`: resumen de perfil
   - `suggested_highlights`: lista de bullet points
   - `suggested_skills_section`: skills en formato RenderCV
   - `suggested_yaml_fragment`: fragmento YAML listo para copiar/pegar en el CV
   - `suggested_cv_patch`: objeto JSON para merge directo

### Búsqueda de Skills (independiente)

- `GET /api/v1/esco/skills/search?text=python&language=es&limit=10` búsqueda de skills
- `GET /api/v1/esco/occupations/details?uri=...` detalles completos de una ocupación
- `GET /api/v1/esco/skills/details?uri=...` detalles completos de una skill

## Experimento instrumental (A/B)

El flujo experimental guarda sesiones, eventos, habilidades y encuestas. Las marcas de tiempo las
pone **el servidor** en UTC (nunca el navegador), y TimeToCV, cobertura ESCO y puntaje ATS se
calculan en el servidor a partir de esos registros.

- **Grupo A (control):** formulario manual. El back rechaza habilidades con URI ESCO para este grupo.
- **Grupo B (AutoCV):** sugerencias ESCO y optimización ATS.
- La asignación es aleatoria por bloques (ningún grupo se adelanta más de 2 sesiones).

### Eventos

| Evento | Quién lo registra | Alimenta |
|---|---|---|
| `consent_given`, `session_start` | `POST /sessions` (requiere `consent: true`) | Grupo, inicio de TimeToCV |
| `section_enter`, `section_complete` | cliente → `POST /sessions/{id}/events` | Tiempo por sección (el servidor calcula los segundos) |
| `field_edit` | cliente (al confirmar un campo) y al quitar habilidades | Ediciones |
| `skill_added`, `skill_normalized` | `POST /sessions/{id}/skills` | Cobertura ESCO |
| `ats_scored`, `cv_export` | `POST /sessions/{id}/export` (solo la primera fija TimeToCV) | ATS y TimeToCV |
| `survey_submitted` | `POST /sessions/{id}/survey` | Satisfacción |
| `session_end` | `POST /sessions/{id}/end` | Sesiones completas / abandonadas |

Puntaje ATS: `25·S + 15·P + 15·H + 20·E + 10·C + 15·F` (ver `app/services/implementations/ats_service.py`).

### Endpoints

- `POST /api/v1/experiment/sessions`, `GET /api/v1/experiment/sessions/{id}`
- `POST /api/v1/experiment/sessions/{id}/events`
- `GET|POST /api/v1/experiment/sessions/{id}/skills`, `DELETE .../skills/{skill_id}` (borrado lógico)
- `GET /api/v1/experiment/sessions/{id}/metrics` métricas en vivo de una sesión
- `POST /api/v1/experiment/ats/preview` puntaje ATS estimado sin registrar nada
- `POST /api/v1/experiment/sessions/{id}/export`, `/survey`, `/end`
- `GET /api/v1/experiment/metrics` métricas por grupo A vs B (con metas)
- `GET /api/v1/experiment/sessions?group=&limit=&offset=` y `/events?session_id=&limit=`
- `GET /api/v1/experiment/export/{sessions|events|skills|survey}.csv` (UTF-8 con BOM para Excel)
- `GET /api/v1/esco/skills/suggest` autocompletado rápido de habilidades
- `GET /api/v1/catalog/cities?country=CO&text=` y `/catalog/institutions?text=`

Si ESCO no responde, sus endpoints devuelven listas vacías con el header `X-ESCO-Degraded: 1`.

### Variables

- `EXPERIMENT_ALLOW_FORCED_GROUP=true` permite forzar el grupo al crear la sesión (solo desarrollo).
- `RESEARCH_API_KEY` protege las rutas de lectura masiva (`/metrics`, `/sessions`, `/events`, `/export/*`)
  con el header `X-Research-Key`. Si está vacía, quedan abiertas.

### Base de datos

Las tablas se crean al iniciar FastAPI (`create_all`), pero **`create_all` no altera tablas que ya
existen**. En una base que ya tenía el esquema del corte anterior, ejecuta:

```bash
psql "postgresql://usuario:clave@host:5432/bautocv" -f sql/001_experiment_schema.sql
psql "postgresql://usuario:clave@host:5432/bautocv" -v app_role=<rol_de_la_api> -f sql/002_instrumentation.sql
```

`002_instrumentation.sql` añade las columnas nuevas y un trigger que impide `UPDATE` y `DELETE` en
`EVENT_LOG` (registro a prueba de manipulación). Por ese trigger, una sesión no se puede borrar
mientras tenga eventos.

### Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Los tests usan SQLite en un archivo temporal. Para probar contra PostgreSQL, define `DATABASE_URL_TEST`.

## PostgreSQL Hosting Sencillo

Puedes usar proveedores gestionados como Render, Supabase, Neon o Railway.
Solo reemplaza `DATABASE_URL` en `.env.prod`.

## RenderCV

La integracion inicial usa un servicio dedicado (`RenderCvService`) y se activa con:

- `RENDERCV_ENABLED=true`
- `RENDERCV_BIN=rendercv`

Luego el endpoint `POST /api/v1/cv/render` recibe YAML de RenderCV y dispara la CLI.

## Variables Sensibles en .env

Configura por ambiente en `.env.dev` o `.env.prod`:

```bash
# OCR (ocr.space)
OCR_SPACE_API_KEY=tu_api_key_de_ocr_space
OCR_SPACE_ENDPOINT=https://api.ocr.space/parse/image
OCR_DEFAULT_LANGUAGE=spa
OCR_TIMEOUT_SECONDS=30

# Gemini (opcional para estructurar mejor OCR)
GEMINI_API_KEY=tu_api_key_de_gemini
GEMINI_MODEL=gemini-1.5-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_TIMEOUT_SECONDS=20
```
