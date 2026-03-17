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

## PostgreSQL Hosting Sencillo

Puedes usar proveedores gestionados como Render, Supabase, Neon o Railway.
Solo reemplaza `DATABASE_URL` en `.env.prod`.

## RenderCV

La integracion inicial usa un servicio dedicado (`RenderCvService`) y se activa con:

- `RENDERCV_ENABLED=true`
- `RENDERCV_BIN=rendercv`

Luego el endpoint `POST /api/v1/cv/render` recibe YAML de RenderCV y dispara la CLI.
