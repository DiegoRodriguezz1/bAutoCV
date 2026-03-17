# ESCO Integration: CV Assistant Workflow

## Overview

This integration enables users to build professional CVs with occupation and skills data from the EU's ESCO taxonomy. The flow is designed to be fast, non-blocking, and cacheable.

## Architecture

- **ESCO Caching**: In-memory TTL cache (default 15 min) with max 512 entries, preventing repeated API calls during development/testing.
- **Parallelized Skills Fetch**: Essential and optional skills loaded concurrently.
- **Fast Autocomplete**: Uses ESCO's `suggest2` endpoint (vs. full-text `search`) for snappy user interactions.
- **Structured Output**: All responses include a ready-to-use YAML fragment for RenderCV.

## Configuration

Add to `.env.<APP_ENV>`:

```bash
# ESCO API base (default: https://ec.europa.eu/esco/api)
ESCO_BASE_URL=https://ec.europa.eu/esco/api

# Timeout in seconds for ESCO HTTP requests (default: 10.0)
ESCO_TIMEOUT_SECONDS=10.0

# Cache TTL in seconds (default: 900 = 15 min)
ESCO_CACHE_TTL_SECONDS=900

# Max entries in in-memory cache (default: 512)
ESCO_CACHE_MAX_ENTRIES=512

# Optional: ESCO dataset version to pin (default: None = latest)
ESCO_SELECTED_VERSION=

```

## Step-by-Step Flow

### Step 1: User Searches for Occupation

**Request:**
```bash
curl -X GET 'http://localhost:8000/api/v1/esco/occupations/suggest' \
  -H 'Content-Type: application/json' \
  -G \
  --data-urlencode 'text=java developer' \
  --data-urlencode 'language=es' \
  --data-urlencode 'limit=5'
```

**Response:**
```json
{
  "occupations": [
    {
      "uri": "http://data.europa.eu/esco/occupation/...",
      "title": "Desarrollador de software/desarrolladora de software",
      "code": "2512.3",
      "search_hit": "desarrolladora de software",
      "description": "...",
      "alternative_labels": ["programmer", "software engineer"]
    },
    ...
  ],
  "total": 18
}
```

### Step 2: Load Occupation Details + Skills

Once the user selects an occupation, fetch its essential and optional skills.

**Request:**
```bash
curl -X GET 'http://localhost:8000/api/v1/esco/occupations/skills' \
  -H 'Content-Type: application/json' \
  -G \
  --data-urlencode 'occupation_uri=http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1' \
  --data-urlencode 'language=es' \
  --data-urlencode 'limit=20'
```

**Response:**
```json
{
  "occupation": {
    "uri": "...",
    "title": "Desarrollador de software",
    "description": "...",
    "alternative_labels": [],
    "code": "2512.3",
    "search_hit": null
  },
  "essential_skills": [
    {
      "uri": "http://data.europa.eu/esco/skill/be48353d-25c7-...",
      "title": "interpretar los requisitos técnicos",
      "description": "...",
      "skill_type": "skill",
      "reuse_level": "sector-specific",
      "alternative_labels": []
    },
    ...
  ],
  "optional_skills": [
    {
      "uri": "http://data.europa.eu/esco/skill/0cd6dcf1-5778-...",
      "title": "Common Lisp",
      "description": null,
      "skill_type": "knowledge",
      "reuse_level": "sector-specific",
      "alternative_labels": []
    },
    ...
  ]
}
```

### Step 3: Generate Description + YAML Fragment

The user selects specific skills and optionally adds context. The endpoint builds a complete professional summary and YAML snippet.

**Request:**
```bash
curl -X POST 'http://localhost:8000/api/v1/esco/occupations/description-assistant' \
  -H 'Content-Type: application/json' \
  -d '{
    "occupation_uri": "http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1",
    "selected_skill_uris": [
      "http://data.europa.eu/esco/skill/be48353d-25c7-4f86-bea9-7b9e248fbc6e",
      "http://data.europa.eu/esco/skill/f28617ad-afdd-4041-814c-216153a38998",
      "http://data.europa.eu/esco/skill/21d2f96d-35f7-4e3f-9745-c533d2dd6e97"
    ],
    "language": "es",
    "additional_context": [
      "8 años en startups de tecnología",
      "Experiencia con metodologías ágiles"
    ],
    "skill_limit": 12
  }'
```

**Response:**
```json
{
  "occupation": { ... },
  "selected_skills": [...],
  "essential_skills": [...],
  "optional_skills": [...],
  "suggested_headline": "Desarrollador de software",
  "suggested_summary": "Perfil orientado a desarrollador de software, con capacidad para traducir requerimientos en entregables concretos y sostenibles. Fuerte en interpretar los requisitos técnicos, analizar especificaciones de software y programación informática. 8 años en startups de tecnología. Experiencia con metodologías ágiles.",
  "suggested_highlights": [
    "Aplicar buenas practicas alineadas con el perfil de desarrollador de software.",
    "Traducir requerimientos funcionales y tecnicos en tareas implementables y medibles.",
    "Demostrar dominio en interpretar los requisitos técnicos dentro de flujos de trabajo reales.",
    "Demostrar dominio en analizar especificaciones de software dentro de flujos de trabajo reales.",
    "Demostrar dominio en programación informática dentro de flujos de trabajo reales."
  ],
  "suggested_skills_section": [
    {
      "label": "Competencias ESCO",
      "details": "interpretar los requisitos técnicos, analizar especificaciones de software y programación informática"
    }
  ],
  "suggested_cv_patch": {
    "headline": "Desarrollador de software",
    "sections": {
      "Perfil profesional": ["..."],
      "Logros o enfoque profesional": [
        {"bullet": "..."},
        {"bullet": "..."}
      ],
      "Habilidades clave": [...]
    }
  },
  "suggested_yaml_fragment": "headline: Desarrollador de software\nsections:\n  Perfil profesional:\n  - '...'\n  ..."
}
```

### Step 4: Generate/Render CV

Use the suggested YAML or patch it into your existing CV, then render.

**Request:**
```bash
curl -X POST 'http://localhost:8000/api/v1/cv/render' \
  -H 'Content-Type: application/json' \
  -d '{
    "profile_yaml": "cv:\n  name: John Doe\n  headline: Desarrollador de software\n...",
    "design": {"theme": "classic"},
    "locale": {"language": "spanish"},
    "output_name": "john_doe_cv"
  }'
```

## Tips & Best Practices

1. **Caching**: The service caches ESCO results by request fingerprint (path + normalized params). Cache is automatically evicted after TTL or when the max entries limit is reached. To skip cache for a request, the service would need to track a query param (future feature).

2. **Language Fallback**: When extracting text from ESCO payloads, the service prefers the requested language, then falls back to Spanish, English, and English-US. This ensures a non-null title even if translation is missing in ESCO.

3. **Parallel Skill Fetch**: Essential and optional skills are fetched concurrently, cutting response time ~50% vs. sequential.

4. **Structured Entry Types**: The CV schema now supports all RenderCV entry types (Education, Experience, Publication, OneLineEntry, Bullet, etc.) as proper Pydantic models. This enables better IDE support and validation.

5. **YAML Generation**: The `POST /api/v1/cv/yaml` endpoint lets you preview the YAML without rendering PDF. Useful for debugging or client-side editing.

## Errors & Recovery

- **Occupation/Skill Not Found**: Returns `200` with empty arrays. Check the `occupation_uri` is correct.
- **ESCO Timeout**: Falls back to `essential_skills=[], optional_skills=[]`. The occupation is still returned.
- **Cache Full**: Oldest entries are evicted FIFO once max capacity is reached.
- **Invalid Language**: Falls back to English (en) or the first available language in ESCO.

## Future Enhancements

- [ ] Add skill similarity matching to suggest related skills
- [ ] Persist cache to Redis for multi-instance deployments
- [ ] Add `description_length` parameter to customize summary length
- [ ] Export CV template snippets per occupation
