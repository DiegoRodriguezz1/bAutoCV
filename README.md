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

```powershell
# PowerShell
$env:APP_ENV="dev"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

```bash
# Bash
export APP_ENV=dev
./.venv/Scripts/python.exe -m uvicorn main:app --reload
```

## Swagger

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Endpoints Base

- `GET /` estado simple del servicio
- `GET /api/v1/health` estado de app y conexion DB
- `POST /api/v1/cv/render` inicio de integracion RenderCV

## PostgreSQL Hosting Sencillo

Puedes usar proveedores gestionados como Render, Supabase, Neon o Railway.
Solo reemplaza `DATABASE_URL` en `.env.prod`.

## RenderCV

La integracion inicial usa un servicio dedicado (`RenderCvService`) y se activa con:

- `RENDERCV_ENABLED=true`
- `RENDERCV_BIN=rendercv`

Luego el endpoint `POST /api/v1/cv/render` recibe YAML de RenderCV y dispara la CLI.
