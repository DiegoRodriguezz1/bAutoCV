# ⚡ RenderCV Quick Reference Card

## 🔴 EL ERROR QUE TUVISTE

```json
{
  "settings": {
    "current_date": 1773964657637  // ❌ TIMESTAMP - INCORRECTO
  }
}
```

### ✅ SOLUCIÓN

```json
{
  "settings": {
    "current_date": "today"  // ✅ STRING - CORRECTO
    // O: "2026-03-19"
  }
}
```

---

## 🎯 Regla de Oro

**`current_date` SIEMPRE debe ser un STRING en uno de estos formatos:**

| Formato | Ejemplo | Válido? |
|---------|---------|---------|
| `"today"` | `"today"` | ✅ |
| `YYYY-MM-DD` | `"2026-03-19"` | ✅ |
| Timestamp | `1773964657637` | ❌ |
| Número | `2026` | ❌ |
| `null` | `null` | ❌ |

---

## 📝 Payload MÍNIMO (Copia/Pega)

```json
{
  "cv": {
    "name": "Tu Nombre"
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

**Endpoint:** `POST /api/v1/cv/render`

---

## ⚙️ Checklist de Tipos de Datos

```javascript
{
  "cv": {
    "name": "string ✅",           // No puede estar vacío
    "headline": "string ✅",       // Opcional
    "email": "string OR [string] ✅",  // Opcional
    "phone": "string OR [string] ✅",  // Opcional
    "sections": {
      "nombre": [
        "string ✅",               // O un objeto
        {
          "institution": "string ✅",
          "start_date": "YYYY-MM ✅",    // O YYYY-MM-DD
          "end_date": "present ✅",      // O YYYY-MM-DD
          "highlights": ["string ✅"]
        }
      ]
    }
  },
  "design": {
    "theme": "classic ✅"          // "classic" | "modern" | "casual"
  },
  "locale": {
    "language": "spanish ✅"       // spanish | english | etc
  },
  "settings": {
    "current_date": "today ✅"     // NUNCA número ni null
  },
  "output_name": "nombre_archivo ✅"  // Opcional
}
```

---

## 🎨 Temas Disponibles para `design.theme`

**Solo se permiten estos tres temas:**

| Tema | Código | Descripción |
|------|--------|------------|
| Classic | `"classic"` | Profesional, limpio, minimalista (por defecto) |
| Modern | `"modern"` | Diseño moderno, layout actualizado |
| Casual | `"casual"` | Informal, creativo, dinámico |

**✅ CORRECTO:**
```json
{
  "design": {
    "theme": "classic"  // OK
  }
}
```

**❌ INCORRECTO:**
```json
{
  "design": {
    "theme": "professional"  // Error: no existe
  }
}
```

---

| ❌ INCORRECTO | ✅ CORRECTO |
|---------------|-----------|
| `"current_date": 1773964657637` | `"current_date": "today"` |
| `"current_date": null` | `"current_date": "2026-03-19"` |
| `"end_date": "present"` (Date object) | `"end_date": "present"` (string) |
| Sin `"name"` en `cv` | Con `"cv": { "name": "..." }` |
| `profile_yaml: null, cv: null` | Al menos uno definido |

---

## 🔧 Generar Fecha Actual (Copia/Pega)

### JavaScript
```javascript
new Date().toISOString().split('T')[0]  // "2026-03-19"
```

### React
```jsx
{
  settings: {
    current_date: new Date().toISOString().split('T')[0]
  }
}
```

### TypeScript
```typescript
const today: string = new Date().toISOString().split('T')[0];
```

### Python
```python
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
```

---

## 🌐 Endpoints

| Endpoint | Método | Resultado |
|----------|--------|----------|
| `/api/v1/cv/render` | POST | PDF + YAML (base64) |
| `/api/v1/cv/yaml` | POST | YAML sin renderizar |
| `/api/v1/cv/download/{filename}` | GET | Descarga PDF |

---

## 🛠️ Validación Rápida en Frontend

```javascript
// ✅ current_date válido?
const date = "2026-03-19";
const isValid = date === "today" || /^\d{4}-\d{2}-\d{2}$/.test(date);
console.log(isValid); // true

// ❌ current_date inválido?
const date2 = 1773964657637;
const isValid2 = typeof date2 === "string";
console.log(isValid2); // false
```

---

## 📋 Tu JSON Anterior (CORREGIDO)

Solo cambió `current_date`:

```json
{
  "cv": {
    "name": "Diego Alejandro Rodríguez Hernández",
    "headline": "Desarrollador Junior | Soporte Técnico TI",
    "location": "Bogotá D.C., Colombia",
    "email": "diegoalejandro619@gmail.com",
    "phone": "+57 305 397 3956",
    "social_networks": [
      { "network": "GitHub", "username": "DiegoRodriguezz1" }
    ],
    "sections": {
      "Sobre mí": [
        "Profesional proactivo, orientado a resultados y con enfoque analítico para la resolución de problemas.",
        "Experiencia en desarrollo de software, soporte técnico y gestión de infraestructura tecnológica.",
        "Capacidad para trabajar con metodologías ágiles y adaptarse a entornos dinámicos."
      ],
      "Educación": [
        {
          "institution": "Escuela Tecnológica Instituto Técnico Central",
          "area": "Ingeniería de Sistemas",
          "degree": "Ingeniería",
          "start_date": "2023-06",
          "end_date": "present",
          "location": "Colombia",
          "highlights": ["Programación Orientada a Objetos en Java", "Bases de datos MySQL", "Sistemas operativos y arquitectura de computadores", "Redes e infraestructura TI"]
        },
        {
          "institution": "Servicio Nacional de Aprendizaje (SENA)",
          "area": "Análisis y Desarrollo de Sistemas de Información",
          "degree": "Tecnólogo",
          "start_date": "2022-01",
          "end_date": "2024-01",
          "location": "Colombia",
          "highlights": ["Desarrollo de aplicaciones en Java", "Modelado y gestión de bases de datos MySQL", "Administración básica de Windows Server"]
        }
      ],
      "Experiencia": [
        {
          "company": "Contratista Independiente",
          "position": "Desarrollador Junior",
          "start_date": "2024-02",
          "end_date": "present",
          "location": "Colombia",
          "summary": "Desarrollo, mantenimiento y soporte de aplicaciones empresariales.",
          "highlights": ["Desarrollo bajo metodologías ágiles (Scrum)", "Atención de requerimientos, soporte técnico y mantenimiento evolutivo", "Implementación de procesos CI/CD", "Manejo de AWS (Lambda, S3, Clusters)", "Uso de Microsoft Azure", "Administración de entornos Red Hat (OpenShift, RHEL, JBoss EAP)", "Gestión de bases de datos Oracle e Informix"]
        }
      ],
      "Habilidades": [
        { "label": "Desarrollo de Software", "details": "Java, Spring Boot, FastAPI, Angular, React, Laravel." },
        { "label": "Bases de Datos", "details": "Oracle, Informix, MySQL." },
        { "label": "Infraestructura y Cloud", "details": "AWS, Microsoft Azure, OpenShift, RHEL, JBoss EAP." },
        { "label": "Metodologías y Herramientas", "details": "Metodologías ágiles (Scrum), Git, CI/CD." },
        { "label": "Sistemas Operativos", "details": "Windows, Linux (RHEL)." },
        { "label": "Habilidades Blandas", "details": "Comunicación efectiva, pensamiento crítico, adaptabilidad y trabajo en equipo." }
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
  "output_name": "diego_rodriguez_cv"
}
```

---

## 🚀 Atajos

**No quiero leer nada, solo quiero que funcione:**

1. Copia el JSON anterior ⬆️
2. Reemplaza valores en `cv` section
3. Asegúrate: `"current_date": "today"`
4. Envía a `POST /api/v1/cv/render`
5. ✅ Listo

---

## 🆘 "Aún no funciona"

Pasos en orden:

1. Prueba con payload MÍNIMO arriba ↑
2. Abre DevTools (F12) → Network
3. Inspecciona qué estás enviando realmente
4. Verifica que `current_date` sea STRING (con comillas `"`)
5. Ve a https://jsonlint.com y pega tu JSON
6. Si JSONLint dice OK, el problema está en el backend (reporta)

---

## 📚 Documentos Completos

- **RENDERCV_REQUEST_GUIDE.md** - Especificación detallada de TODOS los campos
- **RENDERCV_EXAMPLES.md** - Ejemplos en JavaScript, React, Python, cURL, Postman
- **RENDERCV_QUICK_REFERENCE.md** - Este archivo (solo lo esencial)

---

## 💡 Resumen Ejecutivo

| Aspecto | Valor |
|--------|-------|
| **Error actual** | `current_date` es número, debe ser string |
| **Solución** | Usa `"today"` o `"YYYY-MM-DD"` |
| **Endpoint** | `POST /api/v1/cv/render` |
| **Tiempo Aprox.** | 2-5 segundos para generar PDF |
| **Tamaño Respuesta** | PDF en base64 (~100-500KB) |
| **Uso** | Desde frontend → backend → RenderCV |

---

**¡Eso es todo lo que necesitas! 🎉**

Prueba ahora con el JSON MÍNIMO y reporta si funciona.
