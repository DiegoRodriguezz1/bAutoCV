# RenderCV Request Guide - Guía Completa

## 📋 Tabla de Contenidos
1. [Validaciones Principales](#validaciones-principales)
2. [Estructura del Payload](#estructura-del-payload)
3. [Detalles de Cada Campo](#detalles-de-cada-campo)
4. [Valores por Defecto Recomendados](#valores-por-defecto-recomendados)
5. [Ejemplos Correctos](#ejemplos-correctos)
6. [Errores Comunes y Soluciones](#errores-comunes-y-soluciones)
7. [Endpoints Disponibles](#endpoints-disponibles)

---

## ⚠️ Validaciones Principales

**El backend valida:**

| Campo | Validación | Error Si |
|-------|-----------|---------|
| `profile_yaml` O `cv` | Al menos uno debe estar presente | Ambos son null/undefined |
| `cv.name` | Requerido si usas `cv` | No se proporciona |
| `settings.current_date` | Formato: `YYYY-MM-DD` o `"today"` | Timestamp, otro formato, null |
| Fechas en entries | Formato: `YYYY-MM-DD` o `"present"` | Otro formato |
| `design.theme` | String legal de RenderCV | Valor inválido |
| `locale.language` | String válido de idioma | Idioma no soportado |

---

## 🔧 Estructura del Payload

```json
{
  "profile_yaml": null,
  "cv": {
    "name": "string (REQUERIDO)",
    "headline": "string (opcional)",
    "location": "string (opcional)",
    "email": "string | [string] (opcional)",
    "phone": "string | [string] (opcional)",
    "website": "string | [string] (opcional)",
    "photo": "string (opcional, ruta o URL)",
    "social_networks": [
      {
        "network": "string",
        "username": "string"
      }
    ],
    "sections": {
      "section_name": [
        "Opción A: string simple",
        "Opción B: estructura compleja (ver abajo)"
      ]
    }
  },
  "design": {
    "theme": "classic (por defecto) | modern | string válido"
  },
  "locale": {
    "language": "spanish"
  },
  "settings": {
    "current_date": "YYYY-MM-DD o 'today'"
  },
  "output_name": "diego_rodriguez_cv (opcional)"
}
```

---

## 📖 Detalles de Cada Campo

### 1. **`profile_yaml`** vs **`cv`** (Elige UNO)

#### Opción A: `profile_yaml` (String YAML completo)
```json
{
  "profile_yaml": "cv:\n  name: Diego\n  headline: Developer\ndesign:\n  theme: classic\n...",
  "cv": null
}
```
- Uso: Si ya tienes YAML listo
- Ventaja: Control total sobre la estructura
- RenderCV lo interpreta directamente

#### Opción B: `cv` (Objeto estructurado - RECOMENDADO)
```json
{
  "profile_yaml": null,
  "cv": {
    "name": "Diego",
    "headline": "Developer",
    "sections": { ... }
  }
}
```
- Uso: Construcción dinámica desde el frontend
- Ventaja: Validación automática en el backend
- El backend convierte esto a YAML

**❌ NO HAGAS ESTO:**
```json
{
  "profile_yaml": null,
  "cv": null  // Error: Se requiere al menos uno
}
```

---

### 2. **`cv`** - Datos Personales

| Campo | Tipo | Obligatorio | Ejemplo | Validación |
|-------|------|------------|---------|-----------|
| `name` | `string` | ✅ SÍ | `"Diego Alejandro Rodríguez"` | No vacío |
| `headline` | `string` | ❌ No | `"Desarrollador Junior"` | - |
| `location` | `string` | ❌ No | `"Bogotá, Colombia"` | - |
| `email` | `string` OR `[string]` | ❌ No | `"email@example.com"` o `["email1@", "email2@"]` | Validación básica de @ |
| `phone` | `string` OR `[string]` | ❌ No | `"+57 305 397 3956"` o array | - |
| `website` | `string` OR `[string]` | ❌ No | `"https://example.com"` | - |
| `photo` | `string` | ❌ No | `"/path/to/photo.jpg"` | - |
| `social_networks` | `array` | ❌ No | Ver abajo ↓ | - |

#### **Social Networks**
```json
"social_networks": [
  {
    "network": "GitHub",
    "username": "DiegoRodriguezz1"
  },
  {
    "network": "LinkedIn",
    "username": "diego-rodriguez"
  }
]
```

---

### 3. **`cv.sections`** - Secciones del CV

Las secciones pueden contener:
- **Strings simples** (para texto libre)
- **Objetos estructurados** (para Education, Experience, etc.)

```json
"sections": {
  "Sobre mí": [
    "Párrafo 1 como string",
    "Párrafo 2 como string"
  ],
  "Educación": [
    { /* Objeto Education */ },
    { /* Otro Objeto Education */ }
  ],
  "Habilidades": [
    { "label": "Python", "details": "Experto" },
    { "label": "Java", "details": "Intermedio" }
  ]
}
```

#### **Tipos de Entry (Estructuras)**

##### A. **Education**
```json
{
  "institution": "Universidad X",
  "area": "Ingeniería de Sistemas",
  "degree": "Carrera",
  "start_date": "2022-01",
  "end_date": "2024-06",
  "location": "Bogotá, Colombia",
  "highlights": [
    "Título 1",
    "Título 2"
  ]
}
```

##### B. **Experience**
```json
{
  "company": "Empresa X",
  "position": "Desarrollador Junior",
  "start_date": "2024-02",
  "end_date": "present",
  "location": "Bogotá, Colombia",
  "summary": "Resumen breve del rol",
  "highlights": [
    "Logro 1",
    "Logro 2"
  ]
}
```

##### C. **One Line Entry** (Para habilidades, lenguajes, etc.)
```json
{
  "label": "Desarrollo de Software",
  "details": "Java, Spring Boot, FastAPI, Angular, React"
}
```

##### D. **Normal Entry**
```json
{
  "name": "Nombre del proyecto o item",
  "start_date": "2023-06",
  "end_date": "2024-01",
  "highlights": ["Detalle 1", "Detalle 2"]
}
```

##### E. **Publication Entry**
```json
{
  "title": "Título de publicación",
  "authors": ["Autor 1", "Autor 2"],
  "date": "2024-03",
  "journal": "Nombre de revista",
  "doi": "10.xxxx/xxxxx",
  "url": "https://example.com"
}
```

##### F. **Bullet Entry** (Punto simple)
```json
{
  "bullet": "Este es un punto de lista"
}
```

##### G. **Numbered Entry**
```json
{
  "number": "1"
}
```

##### H. **Reversed Numbered Entry**
```json
{
  "number": "5"
}
```

---

### 4. **`design`** - Configuración de Diseño

**Solo se permite usar los siguientes temas:**

| Campo | Valor | Descripción |
|-------|-------|------------|
| `theme` | `"classic"` | ✅ Tema profesional y limpio (por defecto) |
| `theme` | `"modern"` | ✅ Tema moderno y minimalista |
| `theme` | `"casual"` | ✅ Tema informal y creativo |

```json
"design": {
  "theme": "classic"
}
```

**✅ Valores válidos:**
```json
{
  "design": { "theme": "classic" }
  // O:
  // "design": { "theme": "modern" }
  // O:
  // "design": { "theme": "casual" }
}
```

**❌ Valores inválidos (causan error):**
```json
{
  "design": { "theme": "professional" }  // Error: no existe
}
```

---

### 5. **`locale`** - Localización de Idioma

| Campo | Valor | Descripción |
|-------|-------|------------|
| `language` | `"spanish"` | CV en español |
| `language` | `"english"` | CV en inglés |
| `language` | `"portuguese"` | CV en portugués |
| `language` | Otro código | Si RenderCV lo soporta |

```json
"locale": {
  "language": "spanish"
}
```

---

### 6. **`settings`** - Configuración de RenderCV

**⚠️ CAMPO MÁS CRÍTICO: `current_date`**

```json
"settings": {
  "current_date": "2026-03-19"
}
```

| Campo | Tipo | Formato Válido | Ejemplo | ❌ INVÁLIDO |
|-------|------|---|---------|----------|
| `current_date` | `string` | `YYYY-MM-DD` | `"2026-03-19"` | `1773964657637` (timestamp) |
| `current_date` | `string` | literal `"today"` | `"today"` | `null`, `undefined` |

**✅ CORRECTO:**
```json
{ "settings": { "current_date": "2026-03-19" } }
{ "settings": { "current_date": "today" } }
```

**❌ INCORRECTO:**
```json
{ "settings": { "current_date": 1773964657637 } }  // Número timestamp
{ "settings": { "current_date": null } }  // null
{ "settings": { "current_date": "19-03-2026" } }  // Otro formato
```

---

### 7. **`output_name`** - Nombre del archivo generado

```json
{
  "output_name": "diego_rodriguez_cv"
}
```

- Tipo: `string` (opcional)
- El backend añade `.pdf` automáticamente
- Si no se proporciona, genera: `cv_<random8chars>.pdf`
- Ejemplo de salida: `diego_rodriguez_cv.pdf`

---

## 🎯 Valores por Defecto Recomendados

Para que **siempre funcione**, usa esta estructura como template:

```json
{
  "profile_yaml": null,
  "cv": {
    "name": "OBLIGATORIO - Tu nombre aquí",
    "headline": "Tu titular profesional (opcional)",
    "location": "Tu ubicación (opcional)",
    "email": "tu_email@example.com",
    "phone": "+57 305 397 3956",
    "website": "https://github.com/tu-usuario",
    "social_networks": [
      {
        "network": "GitHub",
        "username": "tu-usuario"
      }
    ],
    "sections": {
      "Sobre mí": [
        "Párrafo 1 sobre ti",
        "Párrafo 2 sobre tu experiencia"
      ],
      "Educación": [
        {
          "institution": "Universidad/Instituto",
          "area": "Carrera",
          "degree": "Título",
          "start_date": "2022-01",
          "end_date": "2024-06",
          "location": "País",
          "highlights": [
            "Materia o logro 1",
            "Materia o logro 2"
          ]
        }
      ],
      "Experiencia": [
        {
          "company": "Empresa",
          "position": "Cargo",
          "start_date": "2024-02",
          "end_date": "present",
          "location": "País",
          "summary": "Breve descripción del rol",
          "highlights": [
            "Logro o responsabilidad 1",
            "Logro o responsabilidad 2"
          ]
        }
      ],
      "Habilidades": [
        {
          "label": "Lenguajes",
          "details": "Java, Python, JavaScript"
        },
        {
          "label": "Frameworks",
          "details": "Spring Boot, FastAPI, React"
        }
      ]
    }
  },
  "design": {
    "theme": "classic"
  },
  "locale": {
    "language": "spanish"
  },
  "settings": {
    "current_date": "today"
  },
  "output_name": "mi_cv"
}
```

---

## ✅ Ejemplos Correctos

### Ejemplo Minimal (lo mínimo para que funcione)

```json
{
  "cv": {
    "name": "Diego Rodríguez",
    "sections": {
      "Perfil": [
        "Desarrollador con experiencia en Java"
      ]
    }
  },
  "design": {
    "theme": "classic"
  },
  "locale": {
    "language": "spanish"
  },
  "settings": {
    "current_date": "today"
  }
}
```

### Ejemplo Completo (Como en tu JSON anterior)

```json
{
  "cv": {
    "name": "Diego Alejandro Rodríguez Hernández",
    "headline": "Desarrollador Junior | Soporte Técnico TI",
    "location": "Bogotá D.C., Colombia",
    "email": "diegoalejandro619@gmail.com",
    "phone": "+57 305 397 3956",
    "social_networks": [
      {
        "network": "GitHub",
        "username": "DiegoRodriguezz1"
      }
    ],
    "sections": {
      "Sobre mí": [
        "Profesional proactivo, orientado a resultados y con enfoque analítico.",
        "Experiencia en desarrollo de software.",
        "Capacidad para trabajar con metodologías ágiles."
      ],
      "Educación": [
        {
          "institution": "Escuela Tecnológica Instituto Técnico Central",
          "area": "Ingeniería de Sistemas",
          "degree": "Ingeniería",
          "start_date": "2023-06",
          "end_date": "present",
          "location": "Colombia",
          "highlights": [
            "Programación Orientada a Objetos en Java",
            "Bases de datos MySQL"
          ]
        },
        {
          "institution": "SENA",
          "area": "Análisis y Desarrollo de Sistemas",
          "degree": "Tecnólogo",
          "start_date": "2022-01",
          "end_date": "2024-01",
          "location": "Colombia",
          "highlights": [
            "Desarrollo de aplicaciones en Java",
            "MySQL y Windows Server"
          ]
        }
      ],
      "Experiencia": [
        {
          "company": "Contratista Independiente",
          "position": "Desarrollador Junior",
          "start_date": "2024-02",
          "end_date": "present",
          "location": "Colombia",
          "summary": "Desarrollo, mantenimiento de aplicaciones.",
          "highlights": [
            "Metodologías ágiles (Scrum)",
            "Implementación de CI/CD",
            "AWS y Azure"
          ]
        }
      ],
      "Habilidades": [
        {
          "label": "Desarrollo",
          "details": "Java, Spring Boot, FastAPI, Angular, React"
        },
        {
          "label": "Bases de Datos",
          "details": "Oracle, MySQL, Informix"
        },
        {
          "label": "Cloud",
          "details": "AWS, Azure, OpenShift"
        }
      ]
    }
  },
  "design": {
    "theme": "classic"
  },
  "locale": {
    "language": "spanish"
  },
  "settings": {
    "current_date": "2026-03-19"
  },
  "output_name": "diego_rodriguez_cv"
}
```

---

## ❌ Errores Comunes y Soluciones

### Error 1: Invalid `current_date` format

**❌ Entrada (INCORRECTO):**
```json
{
  "settings": {
    "current_date": 1773964657637
  }
}
```

**Error:**
```
This is not a valid `current_date`! Please use YYYY-MM-DD format or "today".
```

**✅ Solución:**
```json
{
  "settings": {
    "current_date": "2026-03-19"
  }
}
```

---

### Error 2: Missing required field `name`

**❌ Entrada (INCORRECTO):**
```json
{
  "cv": {
    "headline": "Developer",
    "sections": { }
  }
}
```

**Error:**
```
Field required
```

**✅ Solución:**
```json
{
  "cv": {
    "name": "Diego Rodríguez",
    "headline": "Developer",
    "sections": { }
  }
}
```

---

### Error 3: Neither `profile_yaml` nor `cv` provided

**❌ Entrada (INCORRECTO):**
```json
{
  "design": { "theme": "classic" },
  "locale": { "language": "spanish" }
}
```

**Error:**
```
Provide either 'profile_yaml' or 'cv'.
```

**✅ Solución:**
```json
{
  "cv": {
    "name": "Diego Rodríguez",
    "sections": {}
  },
  "design": { "theme": "classic" },
  "locale": { "language": "spanish" }
}
```

---

### Error 4: Invalid date format in entry

**❌ Entrada (INCORRECTO):**
```json
{
  "institution": "Universidad X",
  "start_date": "06-2022",
  "end_date": "2024-06"
}
```

**Error:**
```
Invalid date format for start_date
```

**✅ Solución:**
```json
{
  "institution": "Universidad X",
  "start_date": "2022-06",
  "end_date": "2024-06"
}
```

---

### Error 5: `present` en lugar de "present" (string)

**❌ Entrada (INCORRECTO):**
```json
{
  "end_date": present
}
```

**Error:**
```
Syntax error: 'present' is not defined
```

**✅ Solución:**
```json
{
  "end_date": "present"
}
```

---

## 🔌 Endpoints Disponibles

### 1. **Generar PDF (Renderizar)**
```http
POST /api/v1/cv/render
Content-Type: application/json

{
  "cv": { ... },
  "design": { ... },
  "locale": { ... },
  "settings": { ... }
}
```

**Respuesta:**
```json
{
  "accepted": true,
  "message": "PDF generated successfully.",
  "output_path": "generated_cvs/diego_rodriguez_cv.pdf",
  "generated_yaml": "cv:\n  name: Diego...",
  "pdf_base64": "JVBERi0xLjQKJeLjz9MNCjEgMCBvYmo...",
  "filename": "diego_rodriguez_cv.pdf"
}
```

---

### 2. **Generar solo YAML (sin renderizar)**
```http
POST /api/v1/cv/yaml
Content-Type: application/json

{
  "cv": { ... },
  "design": { ... },
  "locale": { ... },
  "settings": { ... }
}
```

**Respuesta:**
```json
{
  "generated_yaml": "cv:\n  name: Diego Alejandro...",
  "document": {
    "cv": { ... },
    "design": { ... }
  }
}
```

---

## 📱 Para el Frontend (JavaScript/TypeScript)

### Función Helper para validar fecha

```javascript
function validateCurrentDate(date) {
  if (typeof date !== 'string') {
    console.error('current_date debe ser string');
    return false;
  }

  if (date === 'today') {
    return true;
  }

  // Validar formato YYYY-MM-DD
  const regex = /^\d{4}-\d{2}-\d{2}$/;
  if (!regex.test(date)) {
    console.error('current_date debe ser "today" o YYYY-MM-DD');
    return false;
  }

  // Validar que sea fecha válida
  const dateObj = new Date(date + 'T00:00:00');
  return !isNaN(dateObj.getTime());
}

// Uso
validateCurrentDate('2026-03-19'); // ✅ true
validateCurrentDate('today'); // ✅ true
validateCurrentDate(1773964657637); // ❌ false
```

### Función para generar fecha actual en YYYY-MM-DD

```javascript
function getCurrentDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Uso en payload
const payload = {
  cv: { ... },
  settings: {
    current_date: getCurrentDateString() // "2026-03-19"
    // O simplemente:
    // current_date: "today"
  }
};
```

---

## 🚀 Checklist para Enviar Petición Correcta

Antes de enviar a `/api/v1/cv/render`, verifica:

- [ ] **`cv.name`** está presente y no vacío
- [ ] **`settings.current_date`** es `"today"` o formato `YYYY-MM-DD`
- [ ] **NO hay `profile_yaml`** si estás usando `cv` (o es `null`)
- [ ] Todas las **fechas en entries** son `YYYY-MM-DD` o `"present"`
- [ ] **`design.theme`** es `"classic"`, `"modern"`, o válido
- [ ] **`locale.language`** es válido (ej: `"spanish"`)
- [ ] No hay **arrays vacíos** en `sections` (opcional completamente)
- [ ] **`social_networks`** tiene `network` y `username` si está presente

---

## 📞 Debugging

Si aún recibas errores, incluye en tu reporte:

1. El **JSON exacto** que estás enviando
2. El **mensaje de error** completo de RenderCV
3. La **sección del payload** donde está el error

Ejemplo de reporte útil:
```
Error: "There are validation errors! Location: settings.current_date"
Payload que envié: { "settings": { "current_date": 1773964657637 } }
```

---

## ✨ Resumen

| Aspecto | Regla |
|--------|-------|
| **API Endpoint** | `POST /api/v1/cv/render` |
| **Al menos uno** | `profile_yaml` O `cv` |
| **Obligatorio si `cv`** | `name` |
| **Formato fecha crítico** | `YYYY-MM-DD` o `"today"` |
| **Defecto recomendado** | `settings.current_date: "today"` |
| **Theme defecto** | `"classic"` |
| **Idioma defecto** | `"spanish"` |
| **Validación frontnen** | NO envíes timestamps, NO envíes null en current_date |

---

¡Ahora tu frontend debería funcionar perfectamente! 🚀
