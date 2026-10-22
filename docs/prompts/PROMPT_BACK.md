# Prompt para el backend (bAutoCV) — Instrumentación del experimento A/B + ESCO

> Pega este prompt completo en el agente que trabaja en el repo **bAutoCV** (FastAPI + SQLAlchemy async + PostgreSQL).
> El frontend (repo AutoCV) lo hace otro agente con `PROMPT_FRONT.md`; la sección **"Contrato de API"** es idéntica en los dos prompts y es lo único que tienen en común. No cambies el contrato sin avisar.

---

## Contexto

AutoCV es un proyecto de investigación de la ETITC (Tecnología en Desarrollo de Software, corte 2). El prototipo tiene que medir **sin intervención manual** estas variables de un experimento A/B:

| Variable | Evento(s) | Fórmula | Meta |
|---|---|---|---|
| Grupo (independiente) | `session_start` | Asignación aleatoria 50/50 | Grupos balanceados |
| TimeToCV (min) | `session_start`, `cv_export` | `(t_export − t_start) / 60` en minutos | Grupo B < 30 min |
| Tiempo por sección (s) | `section_enter`, `section_complete` | `t_complete − t_enter` | Encontrar cuellos de botella |
| Cobertura ESCO (%) | `skill_added`, `skill_normalized` | `# habilidades con URI ESCO / # habilidades × 100` | ≥ 80 % en B |
| Puntaje ATS (0–100) | `ats_scored` | `25·S + 15·P + 15·H + 20·E + 10·C + 15·F` (ver abajo) | ≥ 75 |
| Satisfacción (1–5) | `survey_submitted` | Promedio de 4 ítems Likert | ≥ 4,0 |
| Ediciones | `field_edit` | Conteo por sesión | Referencia |
| InterviewRate | `application_status` | entrevistas / postulaciones × 100 | Solo se deja la tabla |

- **Grupo A (control):** formulario manual, sin sugerencias ESCO ni optimización ATS.
- **Grupo B (AutoCV):** sugerencias ESCO (habilidades y ocupaciones) y optimización ATS.
- Las marcas de tiempo las pone **el servidor** (`now()` de PostgreSQL, UTC), nunca el reloj del navegador.
- `EVENT_LOG` es **solo inserción**: sin UPDATE ni DELETE.
- El consentimiento informado (Ley 1581 de 2012) se registra como `consent_given` **antes** de `session_start`.

### Fórmula ATS (cada factor de 0 a 1)
- **S** = secciones estándar completas / 4 (perfil = nombre + resumen, formación ≥ 1, experiencia ≥ 1, habilidades ≥ 1)
- **P** = resumen de 40 a 120 palabras → 1; de 20 a 39 → 0,5; otro caso → 0
- **H** = min(nº habilidades, 5) / 5
- **E** = cobertura ESCO / 100
- **C** = (correo válido ? 0,5 : 0) + (teléfono con ≥ 7 dígitos ? 0,5 : 0)
- **F** = (≥ 1 formación con periodo ? 0,5 : 0) + (≥ 1 experiencia con periodo ? 0,5 : 0)

Resultado redondeado a entero. Devuelve también el desglose por factor.

## Estado actual (lo que ya existe y lo que falla)

Ya existe `app/controllers/experiment_controller.py`, `app/entities/experiment.py`, `app/schemas/experiment.py`, `sql/001_experiment_schema.sql` y `app/controllers/esco_controller.py` + `esco_service.py` (con caché). Problemas que hay que corregir:

1. `time_to_cv_min`, `esco_coverage_pct` y `ats_score` **nunca se calculan**: las columnas existen pero quedan en NULL.
2. `consent_given` se inserta automáticamente al crear la sesión, sin que el usuario haya aceptado nada.
3. `POST /sessions/{id}/skills` recibe los datos por query string y no registra `skill_added` ni `skill_normalized`.
4. No hay tiempo por sección, ni métricas por grupo, ni CSV de encuestas.
5. Nada impide que el grupo A guarde habilidades normalizadas.
6. `EVENT_LOG` se puede modificar.
7. `GET /metrics` mezcla los dos grupos, cuando lo que interesa es comparar A contra B.

## Tareas

### 1. Modelo de datos
- Crea `sql/002_instrumentation.sql` (idempotente, se puede correr dos veces):
  - `EXPERIMENT_SESSION`: añade `section_times JSONB NOT NULL DEFAULT '{}'`, `ats_breakdown JSONB`, `user_agent TEXT`, `a11y_prefs JSONB` (preferencias de accesibilidad que usó el participante, para el análisis).
  - `SKILL`: añade `normalized_at TIMESTAMPTZ`, `source VARCHAR(20)` (`manual` | `esco_suggestion` | `occupation`), `removed_at TIMESTAMPTZ` (borrado lógico, nunca físico).
  - `SURVEY_RESPONSE`: añade `item SMALLINT` (1–4).
  - `APPLICATION_STATUS`: añade `job_ref TEXT` y un `CHECK (status IN ('enviada','vista','entrevista','rechazada'))`.
  - Trigger `BEFORE UPDATE OR DELETE ON "EVENT_LOG"` que lance una excepción, y `REVOKE UPDATE, DELETE ON "EVENT_LOG" FROM <rol de la app>` (el nombre del rol va como comentario/variable).
  - Cambia `EVENT_LOG.id` a BIGINT en el ORM, para que coincida con el BIGSERIAL.
- Refleja todo en `app/entities/experiment.py`. `create_all` no altera tablas que ya existen, así que documenta en el README que hay que correr `002_instrumentation.sql`.

### 2. Sesiones y consentimiento
- `POST /experiment/sessions` exige `consent: true` (si no, 422). Inserta `consent_given` y luego `session_start`, cada uno con su propio `now()` (sentencias separadas o `clock_timestamp()`, para que no queden con el mismo timestamp de la transacción).
- El `group` forzado (`A`/`B`) solo se acepta si la variable `EXPERIMENT_ALLOW_FORCED_GROUP=true` (útil en desarrollo). Si no, se asigna al azar. Para que los grupos queden balanceados, usa aleatorización por bloques: si la diferencia entre A y B supera 2, se asigna el grupo con menos sesiones; si no, `random`.
- `GET /experiment/sessions/{id}` devuelve el estado de la sesión, para que el front pueda retomarla al recargar la página.

### 3. Eventos
- `POST /experiment/sessions/{id}/events`:
  - `section_enter` lleva `metadata.section` ∈ `personal|education|experience|skills|export`.
  - `section_complete`: el servidor calcula los segundos = `now()` − último `section_enter` de esa sección, los guarda en `metadata.seconds` y los **acumula** en `section_times[section]`, porque el usuario puede volver a una sección.
  - `field_edit` lleva `metadata.field`. El front lo manda al confirmar el campo (blur o change), no en cada tecla. Igual pon un límite de 1 evento por campo cada 2 s por sesión para protegerte.
  - Rechaza eventos (409) si la sesión ya tiene `ended_at`.
  - `cv_export`, `ats_scored`, `skill_added`, `skill_normalized` y `survey_submitted` **no** se aceptan por este endpoint (400): los generan los endpoints dedicados de abajo, para que los cálculos no dependan del cliente.

### 4. Habilidades
- `POST /experiment/sessions/{id}/skills` con body JSON `{ input_label, esco_uri?, preferred_label?, source }`:
  - Siempre registra `skill_added`. Si trae `esco_uri`, registra también `skill_normalized` y llena `normalized_at`.
  - Si la sesión es del grupo **A** y llega `esco_uri` → 400 (protege la integridad del experimento).
  - Deduplica por `lower(trim(input_label))` dentro de la sesión (devuelve la habilidad que ya existe).
  - Valida que `esco_uri` empiece con `http://data.europa.eu/esco/skill/`.
- `DELETE /experiment/sessions/{id}/skills/{skill_id}` → borrado lógico (`removed_at`) + evento `field_edit` con `metadata.field = "skills"`.
- `GET /experiment/sessions/{id}/skills` → lista las habilidades activas.

### 5. Exportación y cálculo de métricas
- `POST /experiment/sessions/{id}/export` con un snapshot del CV (ver contrato):
  - Calcula el ATS con la fórmula, usando **la cobertura ESCO calculada desde la tabla SKILL** (no la que mande el cliente).
  - Guarda `ats_score`, `ats_breakdown`, `esco_coverage_pct` y `exported_at = now()`, y calcula `time_to_cv_min = extract(epoch from exported_at - started_at)/60`, redondeado a 2 decimales.
  - Registra `ats_scored` y luego `cv_export`.
  - **Idempotente:** solo la **primera** exportación fija TimeToCV. Las siguientes registran `cv_export` con `metadata.repeat = true` y no tocan las métricas.
  - Devuelve `{ time_to_cv_min, esco_coverage_pct, ats_score, ats_breakdown, section_times }`.
- Pon la lógica ATS en `app/services/implementations/ats_service.py`, con una función pura y testeable.
- `POST /experiment/ats/preview` (sin sesión, no registra nada): recibe el mismo snapshot más `esco_coverage_pct` y devuelve el puntaje y el desglose. El panel en vivo del front lo usa mientras el usuario llena el formulario.

### 6. Encuesta y cierre
- `POST /experiment/sessions/{id}/survey` con body `{ responses: [{item: 1..4, score: 1..5}] }`. Exige los 4 ítems; no se puede enviar dos veces (409). Calcula `satisfaction` y registra `survey_submitted` con el promedio y los valores.
- `POST /experiment/sessions/{id}/end` → `session_end` + `ended_at`. Requiere que antes exista `cv_export`; si no, la sesión se marca como abandonada con `metadata.abandoned = true`.

### 7. Métricas para la consola del investigador
- `GET /experiment/metrics` devuelve:
  ```json
  {
    "sessions_started": 0, "sessions_completed": 0, "events": 0,
    "by_group": {
      "A": { "n": 0, "time_to_cv_avg": null, "time_to_cv_sd": null, "esco_coverage_avg": null,
             "ats_score_avg": null, "satisfaction_avg": null, "edits_avg": null,
             "section_seconds_avg": { "personal": null, "education": null, "experience": null, "skills": null } },
      "B": { "...igual..." : null }
    },
    "targets": { "time_to_cv_b_max": 30, "esco_coverage_b_min": 80, "ats_min": 75, "satisfaction_min": 4.0 }
  }
  ```
  Solo cuentan para los promedios las sesiones con `exported_at`.
- `GET /experiment/sessions?limit=&offset=&group=` y `GET /experiment/events?session_id=&limit=` con paginación.
- `GET /experiment/sessions/{id}/metrics` → métricas en vivo de una sesión (tiempo transcurrido, section_times, cobertura ESCO actual, nº de habilidades, ediciones).
- CSV: `sessions.csv` (con `section_times` desglosado en columnas `sec_personal_s`, ..., `ats_*` del desglose y `user_agent`), `events.csv` (con `metadata` en JSON), `skills.csv` y `survey.csv`. UTF-8 **con BOM**, para que Excel lea bien las tildes.
- Protege con un header `X-Research-Key` (variable `RESEARCH_API_KEY`) las rutas de lectura masiva (`/metrics`, `/sessions`, `/events`, `/export/*`). Si la variable está vacía, quedan abiertas (modo desarrollo).

### 8. ESCO
- Revisa `esco_service.py`: que use `language=es` con respaldo en `en` cuando no haya etiqueta en español, `selectedVersion` fijo (v1.2.0), y caché.
- Añade `GET /esco/skills/suggest?text=&language=es&limit=8` usando `suggest2` con `type=skill` (más rápido que `search` para autocompletar). Respuesta: `{ skills: [{uri, title, alternative_labels}] }`.
- `GET /esco/occupations/suggest` ya existe: verifica que devuelva `uri`.
- `GET /esco/occupations/skills?occupation_uri=` ya existe. El front lo usa en el grupo B para sugerir habilidades esenciales del cargo elegido.
- Si ESCO no responde (timeout o 5xx), devuelve 200 con lista vacía y el header `X-ESCO-Degraded: 1`, para que el front pueda avisar sin romperse.

### 9. Catálogos para autocompletar (los dos grupos)
- `GET /catalog/cities?country=CO&text=` → ciudades y municipios de Colombia (archivo JSON estático en `app/data/`, con departamento). Para otros países devuelve lista vacía.
- `GET /catalog/institutions?text=` → instituciones de educación superior de Colombia (JSON estático; si no hay fuente a mano, deja una lista inicial de unas 50 con ETITC, SENA, UNAL, U. Distrital, etc. y documenta que hay que completarla con el SNIES).
- Los países los resuelve el front con `Intl.DisplayNames`, no hace falta endpoint.

### 10. Calidad
- Tests con `pytest` + `httpx.AsyncClient`, sobre una BD de prueba o SQLite si es viable (si no, PostgreSQL de prueba por `DATABASE_URL_TEST`):
  - `ats_service`: los casos borde de cada factor.
  - Flujo completo: sesión → secciones → skills (A rechaza URI, B la acepta) → export (TimeToCV > 0 e idempotente) → encuesta → fin.
  - El trigger de `EVENT_LOG` impide UPDATE y DELETE.
- Añade `pytest`, `pytest-asyncio` a `requirements-dev.txt`.
- Actualiza `README.md`: cómo correr las migraciones SQL, las variables nuevas (`EXPERIMENT_ALLOW_FORCED_GROUP`, `RESEARCH_API_KEY`), y la tabla de eventos.
- Agrega las variables nuevas a `.env.example`. No toques `.env.dev` ni `.env.prod` más allá de añadir esas claves vacías.
- CORS: que `CORS_ALLOWED_ORIGINS` incluya `http://localhost:5173` y el dominio de GitHub Pages del front (está en el archivo `CNAME` del repo AutoCV), y que exponga el header `X-ESCO-Degraded`.

## Reglas
- Respeta la estructura actual (controllers / schemas / entities / services). Un router nuevo `catalog_controller.py`.
- No cambies los endpoints de CV/OCR/RenderCV.
- Mensajes de error al cliente en español; código e identificadores en inglés, como está hoy.
- Trabaja en una rama `feat/instrumentacion-experimento`. Commits pequeños por tarea.
- Al terminar: corre los tests, levanta `uvicorn app.main:app --reload` y prueba el flujo completo con `curl` o `/docs`. Reporta qué pasó y qué no.

---

## Contrato de API (compartido con el front)

Base: `{VITE_API_BASE_URL}` = `http://127.0.0.1:8000/api/v1`

| Método | Ruta | Body / query | Respuesta |
|---|---|---|---|
| POST | `/experiment/sessions` | `{ consent: true, group?: "A"\|"B", participant_code?: string, user_agent?: string, a11y_prefs?: object }` | `{ id, group, started_at, consent_given_at }` |
| GET | `/experiment/sessions/{id}` | — | `{ id, group, started_at, exported_at, ended_at, section_times, survey_done: bool }` |
| POST | `/experiment/sessions/{id}/events` | `{ event_type: "section_enter"\|"section_complete"\|"field_edit", detail?: string, metadata?: { section?, field? } }` | `{ id, session_id, event_type, detail, ts, metadata }` |
| GET | `/experiment/sessions/{id}/skills` | — | `[{ id, input_label, esco_uri, preferred_label, source }]` |
| POST | `/experiment/sessions/{id}/skills` | `{ input_label, esco_uri?, preferred_label?, source: "manual"\|"esco_suggestion"\|"occupation" }` | `{ id, input_label, esco_uri, preferred_label, source }` |
| DELETE | `/experiment/sessions/{id}/skills/{skill_id}` | — | `204` |
| GET | `/experiment/sessions/{id}/metrics` | — | `{ elapsed_min, section_times, esco_coverage_pct, skills_count, edits }` |
| POST | `/experiment/ats/preview` | `CvSnapshot & { esco_coverage_pct }` | `{ ats_score, ats_breakdown: { S, P, H, E, C, F } }` |
| POST | `/experiment/sessions/{id}/export` | `CvSnapshot` | `{ time_to_cv_min, esco_coverage_pct, ats_score, ats_breakdown, section_times }` |
| POST | `/experiment/sessions/{id}/survey` | `{ responses: [{ item: 1..4, score: 1..5 }] }` | `{ satisfaction }` |
| POST | `/experiment/sessions/{id}/end` | — | `{ ended_at }` |
| GET | `/experiment/metrics` | header `X-Research-Key` | ver objeto `by_group` arriba |
| GET | `/experiment/sessions` | `?limit&offset&group` | `[SessionRow]` (incluye `section_times`, `ats_score`, etc.) |
| GET | `/experiment/events` | `?session_id&limit` | `[EventRow]` (incluye `group`, `metadata`) |
| GET | `/experiment/export/{sessions\|events\|skills\|survey}.csv` | — | CSV UTF-8 con BOM |
| GET | `/esco/skills/suggest` | `?text&language=es&limit=8` | `{ skills: [{ uri, title, alternative_labels }] }` |
| GET | `/esco/occupations/suggest` | `?text&language=es&limit=8` | `{ occupations: [{ uri, title, alternative_labels }] }` |
| GET | `/esco/occupations/skills` | `?occupation_uri&language=es&limit=15` | `{ occupation, essential_skills, optional_skills }` |
| GET | `/catalog/cities` | `?country=CO&text` | `[{ name, department }]` |
| GET | `/catalog/institutions` | `?text` | `[{ name, city }]` |

```ts
type CvSnapshot = {
  name: string; email: string; phone: string; summary: string;
  education: { degree: string; institution: string; period: string }[];
  experience: { position: string; company: string; period: string }[];
  skills: string[];
};
```

Ítems de la encuesta (en orden 1–4):
1. El CV final representa bien mi perfil
2. El proceso fue fácil de completar
3. Usaría la herramienta para postularme
4. Confío en que el CV pasa filtros ATS
