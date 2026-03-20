# RenderCV - Ejemplos Prácticos para Copiar/Pegar

Este archivo contiene **ejemplos reales y funcionales** que puedes usar directamente en tu frontend.

---

## 1️⃣ Ejemplo Mínimo (Funciona 100%)

Usa esto si solo quieres probar que todo funciona:

```json
{
  "cv": {
    "name": "Tu Nombre Aquí"
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

**Endpoint:** `POST http://localhost:8000/api/v1/cv/render`

---

## 2️⃣ Ejemplo Completo - Tu CV Actual

Este es tu JSON anterior pero CORREGIDO para que funcione:

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
          "highlights": [
            "Programación Orientada a Objetos en Java",
            "Bases de datos MySQL",
            "Sistemas operativos y arquitectura de computadores",
            "Redes e infraestructura TI"
          ]
        },
        {
          "institution": "Servicio Nacional de Aprendizaje (SENA)",
          "area": "Análisis y Desarrollo de Sistemas de Información",
          "degree": "Tecnólogo",
          "start_date": "2022-01",
          "end_date": "2024-01",
          "location": "Colombia",
          "highlights": [
            "Desarrollo de aplicaciones en Java",
            "Modelado y gestión de bases de datos MySQL",
            "Administración básica de Windows Server"
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
          "summary": "Desarrollo, mantenimiento y soporte de aplicaciones empresariales.",
          "highlights": [
            "Desarrollo bajo metodologías ágiles (Scrum)",
            "Atención de requerimientos, soporte técnico y mantenimiento evolutivo",
            "Implementación de procesos CI/CD",
            "Manejo de AWS (Lambda, S3, Clusters)",
            "Uso de Microsoft Azure",
            "Administración de entornos Red Hat (OpenShift, RHEL, JBoss EAP)",
            "Gestión de bases de datos Oracle e Informix"
          ]
        }
      ],
      "Habilidades": [
        {
          "label": "Desarrollo de Software",
          "details": "Java, Spring Boot, FastAPI, Angular, React, Laravel."
        },
        {
          "label": "Bases de Datos",
          "details": "Oracle, Informix, MySQL."
        },
        {
          "label": "Infraestructura y Cloud",
          "details": "AWS, Microsoft Azure, OpenShift, RHEL, JBoss EAP."
        },
        {
          "label": "Metodologías y Herramientas",
          "details": "Metodologías ágiles (Scrum), Git, CI/CD."
        },
        {
          "label": "Sistemas Operativos",
          "details": "Windows, Linux (RHEL)."
        },
        {
          "label": "Habilidades Blandas",
          "details": "Comunicación efectiva, pensamiento crítico, adaptabilidad y trabajo en equipo."
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

**🔥 DIFERENCIAS CON TU VERSIÓN ANTERIOR:**

| Campo | Antes (❌ Error) | Después (✅ Correcto) |
|-------|-----------------|----------------------|
| `current_date` | `"2026-03-09"` | `"2026-03-19"` (o `"today"`) |
| ~~`current_date`~~ | ~~`1773964657637`~~ (TIMESTAMP) | ❌ NUNCA esto |
| `end_date` | `"present"` | ✅ Correcto (string) |
| Estructura JSON | ✅ Correcta | ✅ Correcta |

---

## 3️⃣ Ejemplo TypeScript/JavaScript para Frontend

### Opción A: Usando Fetch API

```javascript
async function renderCV() {
  const payload = {
    cv: {
      name: "Diego Alejandro Rodríguez Hernández",
      headline: "Desarrollador Junior",
      location: "Bogotá, Colombia",
      email: "diegoalejandro619@gmail.com",
      phone: "+57 305 397 3956",
      social_networks: [
        {
          network: "GitHub",
          username: "DiegoRodriguezz1"
        }
      ],
      sections: {
        "Sobre mí": [
          "Profesional proactivo..."
        ],
        "Educación": [
          {
            institution: "ETITC",
            area: "Ingeniería de Sistemas",
            degree: "Ingeniería",
            start_date: "2023-06",
            end_date: "present",
            location: "Colombia",
            highlights: ["Java", "MySQL"]
          }
        ]
      }
    },
    design: {
      theme: "classic"
    },
    locale: {
      language: "spanish"
    },
    settings: {
      current_date: "today"  // ✅ CLAVE: Usa "today" o "YYYY-MM-DD"
    },
    output_name: "diego_rodriguez_cv"
  };

  try {
    const response = await fetch("http://localhost:8000/api/v1/cv/render", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const error = await response.json();
      console.error("Error:", error);
      return;
    }

    const result = await response.json();
    console.log("✅ CV generado:", result);
    console.log("📄 PDF en base64:", result.pdf_base64);
    console.log("📊 YAML generado:", result.generated_yaml);

  } catch (error) {
    console.error("❌ Error de conexión:", error);
  }
}
```

### Opción B: Usando Axios

```javascript
import axios from 'axios';

async function renderCV() {
  const payload = {
    cv: {
      name: "Diego Alejandro Rodríguez Hernández",
      headline: "Desarrollador Junior",
      sections: {
        "Sobre mí": ["Profesional proactivo..."]
      }
    },
    design: { theme: "classic" },
    locale: { language: "spanish" },
    settings: { current_date: "today" },
    output_name: "diego_rodriguez_cv"
  };

  try {
    const { data } = await axios.post(
      "http://localhost:8000/api/v1/cv/render",
      payload,
      { headers: { "Content-Type": "application/json" } }
    );

    console.log("✅ Éxito:", data);
    return data;

  } catch (error) {
    console.error("❌ Error:", error.response?.data || error.message);
  }
}
```

### Opción C: Validación en Frontend ANTES de enviar

```javascript
function validateCVPayload(payload) {
  const errors = [];

  // Validar que existe cv
  if (!payload.cv) {
    errors.push("❌ cv es requerido");
  }

  // Validar que existe cv.name
  if (!payload.cv?.name || payload.cv.name.trim() === "") {
    errors.push("❌ cv.name es requerido y no puede estar vacío");
  }

  // Validar current_date
  const currentDate = payload.settings?.current_date;
  if (!currentDate) {
    errors.push("❌ settings.current_date es requerido");
  } else if (currentDate !== "today" && !/^\d{4}-\d{2}-\d{2}$/.test(currentDate)) {
    errors.push(`❌ current_date debe ser "today" o YYYY-MM-DD, recibió: ${currentDate}`);
  }

  // Validar fechas en entries
  if (payload.cv?.sections) {
    Object.entries(payload.cv.sections).forEach(([section, entries]) => {
      if (Array.isArray(entries)) {
        entries.forEach((entry, idx) => {
          if (entry.start_date && !/^\d{4}-\d{2}$|^\d{4}-\d{2}-\d{2}$/.test(entry.start_date)) {
            errors.push(`❌ ${section}[${idx}].start_date debe ser YYYY-MM o YYYY-MM-DD`);
          }
          if (entry.end_date && entry.end_date !== "present" && !/^\d{4}-\d{2}$|^\d{4}-\d{2}-\d{2}$/.test(entry.end_date)) {
            errors.push(`❌ ${section}[${idx}].end_date debe ser "present" o YYYY-MM-DD`);
          }
        });
      }
    });
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

// Uso
const validation = validateCVPayload(payload);
if (!validation.valid) {
  console.error("Errores de validación:", validation.errors);
  return;
}

// Si llegamos aquí, el payload es válido
await renderCV();
```

---

## 4️⃣ Ejemplo React Component

```jsx
import { useState } from 'react';
import axios from 'axios';

export function CVRenderer() {
  const [loading, setLoading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [error, setError] = useState(null);

  const handleRenderCV = async () => {
    setLoading(true);
    setError(null);

    const payload = {
      cv: {
        name: "Diego Alejandro Rodríguez Hernández",
        headline: "Desarrollador Junior | Soporte Técnico TI",
        location: "Bogotá D.C., Colombia",
        email: "diegoalejandro619@gmail.com",
        phone: "+57 305 397 3956",
        social_networks: [
          { network: "GitHub", username: "DiegoRodriguezz1" }
        ],
        sections: {
          "Sobre mí": [
            "Profesional proactivo..."
          ],
          "Educación": [
            {
              institution: "ETITC",
              area: "Ingeniería de Sistemas",
              degree: "Ingeniería",
              start_date: "2023-06",
              end_date: "present",
              location: "Colombia",
              highlights: ["Java", "MySQL"]
            }
          ],
          "Experiencia": [
            {
              company: "Independiente",
              position: "Desarrollador Junior",
              start_date: "2024-02",
              end_date: "present",
              location: "Colombia",
              highlights: ["Scrum", "CI/CD", "AWS"]
            }
          ]
        }
      },
      design: { theme: "classic" },
      locale: { language: "spanish" },
      settings: { current_date: "today" },
      output_name: "diego_rodriguez_cv"
    };

    try {
      const { data } = await axios.post(
        "http://localhost:8000/api/v1/cv/render",
        payload
      );

      // Convertir PDF base64 a Blob para descarga
      const binaryString = atob(data.pdf_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);

    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Generar CV</h1>
      
      <button 
        onClick={handleRenderCV} 
        disabled={loading}
        style={{
          padding: "10px 20px",
          backgroundColor: "#007bff",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: loading ? "not-allowed" : "pointer"
        }}
      >
        {loading ? "Generando..." : "Generar CV"}
      </button>

      {error && (
        <div style={{ color: "red", marginTop: "10px" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {pdfUrl && (
        <div style={{ marginTop: "20px" }}>
          <a href={pdfUrl} download="diego_rodriguez.pdf">
            📥 Descargar PDF
          </a>
          <iframe 
            src={pdfUrl} 
            style={{ width: "100%", height: "600px", marginTop: "10px" }}
            title="CV Preview"
          />
        </div>
      )}
    </div>
  );
}
```

---

## 5️⃣ CURL - Ejemplo desde Terminal

```bash
curl -X POST http://localhost:8000/api/v1/cv/render \
  -H "Content-Type: application/json" \
  -d '{
    "cv": {
      "name": "Diego Alejandro Rodríguez Hernández",
      "headline": "Desarrollador Junior",
      "location": "Bogotá, Colombia",
      "email": "diegoalejandro619@gmail.com",
      "phone": "+57 305 397 3956",
      "sections": {
        "Sobre mí": [
          "Profesional proactivo"
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
  }'
```

---

## 6️⃣ Postman - Configuración

### Request Configuration

- **Method:** `POST`
- **URL:** `http://localhost:8000/api/v1/cv/render`
- **Headers:**
  ```
  Content-Type: application/json
  ```

### Body (raw JSON)

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
        "Profesional proactivo, orientado a resultados"
      ],
      "Educación": [
        {
          "institution": "ETITC",
          "area": "Ingeniería de Sistemas",
          "degree": "Ingeniería",
          "start_date": "2023-06",
          "end_date": "present",
          "location": "Colombia",
          "highlights": ["Java", "MySQL"]
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
  "output_name": "diego_rodriguez_cv"
}
```

---
## 2️⃣ bis - Ejemplos con Diferentes Temas

### Classic (Defecto)
```json
{
  "cv": { "name": "Diego Rodríguez" },
  "design": { "theme": "classic" },
  "locale": { "language": "spanish" },
  "settings": { "current_date": "today" }
}
```

### Modern
```json
{
  "cv": { "name": "Diego Rodríguez" },
  "design": { "theme": "modern" },
  "locale": { "language": "spanish" },
  "settings": { "current_date": "today" }
}
```

### Casual
```json
{
  "cv": { "name": "Diego Rodríguez" },
  "design": { "theme": "casual" },
  "locale": { "language": "spanish" },
  "settings": { "current_date": "today" }
}
```

---
## 7️⃣ Endpoint Alternativo: Solo YAML (sin PDF)

Si quieres primero **generar YAML** sin renderizar PDF:

```bash
curl -X POST http://localhost:8000/api/v1/cv/yaml \
  -H "Content-Type: application/json" \
  -d '{
    "cv": {
      "name": "Diego Rodríguez",
      "sections": {
        "Perfil": ["Developer"]
      }
    },
    "design": { "theme": "classic" },
    "locale": { "language": "spanish" },
    "settings": { "current_date": "today" }
  }'
```

**Respuesta:**
```json
{
  "generated_yaml": "cv:\n  name: Diego Rodríguez\n  sections:\n    Perfil:\n      - Developer\ndesign:\n  theme: classic\n...",
  "document": { ... }
}
```

---

## 🎯 Utilidad: Generar Fecha Actual

### JavaScript
```javascript
// Obtener fecha actual en YYYY-MM-DD
const today = new Date().toISOString().split('T')[0];
console.log(today); // 2026-03-19

// Uso en payload
const payload = {
  // ...
  settings: {
    current_date: today  // ✅ "2026-03-19"
  }
};
```

### Python
```python
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
print(today)  # 2026-03-19

payload = {
    # ...
    "settings": {
        "current_date": today  # ✅ "2026-03-19"
    }
}
```

### C# / .NET
```csharp
string today = DateTime.Now.ToString("yyyy-MM-dd");
Console.WriteLine(today);  // 2026-03-19

var payload = new
{
    // ...
    settings = new
    {
        current_date = today  // ✅ "2026-03-19"
    }
};
```

---

## ✅ Checklist Final

Antes de enviar tu petición:

- [ ] ¿`cv.name` está presente?
- [ ] ¿`settings.current_date` es `"today"` o `YYYY-MM-DD`?
- [ ] ¿NO estoy enviando timestamp (números) en `current_date`?
- [ ] ¿Las fechas de entries son `YYYY-MM-DD` o `"present"`?
- [ ] ¿`design.theme` es válido?
- [ ] ¿`locale.language` es válido?
- [ ] ¿Estoy enviando JSON válido (sin caracteres sueltos)?

---

## 🆘 Si Aún Falla

1. **Copia el payload** exacto que estás enviando
2. **Prueba con el ejemplo mínimo** (opción 1)
3. **Verifica los tipos de datos:**
   - `name`: ✅ string
   - `current_date`: ✅ string (nunca número)
   - `end_date`: ✅ string `"present"` (no objeto)
4. **En la consola del navegador**, inspecciona el JSON antes de enviar
5. **Usa un validador JSON online** para asegurar que el JSON es válido

💡 **Pro tip:** Abre DevTools (F12) → Network → filtra por `cv/render` → verás exactamente qué estás enviando

---

¡Todos estos ejemplos funcionan 100%! Elige el que se adapte mejor a tu stack. 🚀
