# OCR CV Extraction - Guía Completa

## 📋 Tabla de Contenidos
1. [Visión General](#visión-general)
2. [Flujo de Uso](#flujo-de-uso)
3. [Endpoints](#endpoints)
4. [Ejemplos](#ejemplos)
5. [Validación en Frontend](#validación-en-frontend)
6. [Casos de Uso](#casos-de-uso)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Visión General

La integración OCR permite a los usuarios subir sus CVs en PDF y extraer automáticamente:

- **Datos personales**: Nombre, email, teléfono, ubicación
- **Experiencia laboral**: Empresa, puesto, fechas
- **Educación**: Institución, carrera, año
- **Habilidades**: Lenguajes, frameworks, soft skills

El backend:
1. **Lee el PDF** usando OCR (ocr.space API - ¡gratuita!)
2. **Extrae el texto** con OCR
3. **(Opcional)** Estructura con Gemini AI para mejor precisión
4. **Genera automáticamente** el YAML en formato RenderCV
5. **Devuelve** los datos listos para renderizar

---

## 🔄 Flujo de Uso

### Escenario 1: Usuario sube PDF existente
```
usuario sube PDF
        ↓
backend extrae texto con OCR
        ↓
backend estructura datos (regex o Gemini)
        ↓
backend genera YAML
        ↓
frontend muestra vista previa
        ↓
usuario confirma o edita
        ↓
frontend envía a /cv/render para generar PDF final
```

### Escenario 2: Usuario edita datos extraídos
```
usuario carga OCR preview
        ↓
usuario ve datos extraídos
        ↓
usuario corrige/completa en formulario
        ↓
usuario envía a /cv/render con datos editados
```

---

## 🔌 Endpoints

### 1. **Extract CV from PDF** (Completo)
```http
POST /api/v1/ocr/extract-cv
Content-Type: application/json

{
  "pdf_base64": "JVBERi0xLjQK...",
  "language": "es",
  "use_gemini": true   // Opcional, por defecto true
}
```

**Respuesta:**
```json
{
  "accepted": true,
  "message": "CV data extracted successfully",
  "ocr_text": "Diego Alejandro Rodríguez...",
  "extracted_data": {
    "name": "Diego Alejandro Rodríguez Hernández",
    "email": "diego@example.com",
    "phone": "+57 305 397 3956",
    "location": "Bogotá, Colombia",
    "headline": "Desarrollador Junior",
    "education": [
      {
        "institution": "ETITC",
        "area": "Ingeniería de Sistemas",
        "start_date": "2023-06",
        "end_date": "present"
      }
    ],
    "experience": [
      {
        "company": "Independiente",
        "position": "Desarrollador Jr",
        "start_date": "2024-02",
        "end_date": "present"
      }
    ],
    "skills": ["Java", "Python", "AWS", "MySQL"]
  },
  "suggested_cv_document": {
    "cv": { ... completo RenderCV document ... },
    "design": { "theme": "classic" },
    "locale": { "language": "spanish" },
    "settings": { "current_date": "2026-03-19" }
  },
  "suggested_yaml": "name: Diego Alejandro Rodríguez Hernández\n...",
  "confidence_score": 87.5
}
```

---

### 2. **Preview OCR** (Rápido)
```http
POST /api/v1/ocr/extract-cv-preview
Content-Type: application/json

{
  "pdf_base64": "JVBERi0xLjQK...",
  "language": "es",
  "use_gemini": false  // Siempre usa regex para ser rápido
}
```

**Respuesta:**
```json
{
  "ocr_text": "Diego Alejandro Rodríguez Hernández\n+57 305 397 3956\ndiego@example.com\n...",
  "extracted_data": { ... datos extraídos ... },
  "confidence_score": 87.5
}
```

> **💡 Diferencia:**
> - `/extract-cv`: Usa Gemini (más lento ~5-10s, más preciso)
> - `/extract-cv-preview`: Usa regex (rápido ~2-3s, menos preciso)

---

## 💻 Ejemplos

### JavaScript: Subir PDF y extraer datos

#### Opción A: Usando Fetch API

```javascript
async function extractCVFromPDF(pdfFile) {
  // 1. Convertir archivo a base64
  const base64 = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      // Remover el prefijo "data:application/pdf;base64,"
      const b64 = reader.result.split(',')[1];
      resolve(b64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(pdfFile);
  });

  // 2. Enviar a backend
  const response = await fetch('http://localhost:8000/api/v1/ocr/extract-cv', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      pdf_base64: base64,
      language: 'es',
      use_gemini: true  // Usar Gemini para mejor precisión
    })
  });

  if (!response.ok) {
    const error = await response.json();
    console.error('Error:', error);
    return null;
  }

  const result = await response.json();
  console.log('Extraction successful!', result);
  return result;
}

// Uso:
const fileInput = document.getElementById('pdfInput');
fileInput.addEventListener('change', async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  console.log('Extrayendo datos del PDF...');
  const result = await extractCVFromPDF(file);

  if (result.accepted) {
    console.log('Datos extraídos:', result.extracted_data);
    console.log('CV lista para renderizar:', result.suggested_cv_document);
    
    // Mostrar vista previa
    displayPreview(result.extracted_data);
  }
});
```

#### Opción B: Usando Axios

```javascript
import axios from 'axios';

async function extractCVWithAxios(pdfFile) {
  const base64 = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      resolve(reader.result.split(',')[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(pdfFile);
  });

  try {
    const { data } = await axios.post('/api/v1/ocr/extract-cv', {
      pdf_base64: base64,
      language: 'es',
      use_gemini: true
    });

    return data;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    throw error;
  }
}
```

---

### React Component Completo

```jsx
import { useState } from 'react';
import axios from 'axios';

export function OCRUploader() {
  const [loading, setLoading] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(false);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      // Convertir a base64
      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      // Enviar al backend
      const response = await axios.post('http://localhost:8000/api/v1/ocr/extract-cv', {
        pdf_base64: base64,
        language: 'es',
        use_gemini: true
      });

      if (response.data.accepted) {
        setExtractedData(response.data);
        setPreview(true);
      } else {
        setError(response.data.message);
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRenderCV = async (data) => {
    try {
      const response = await axios.post('/api/v1/cv/render', 
        data.suggested_cv_document
      );
      console.log('CV generado:', response.data);
      // Descargar PDF
      const link = document.createElement('a');
      link.href = `data:application/pdf;base64,${response.data.pdf_base64}`;
      link.download = 'cv.pdf';
      link.click();
    } catch (err) {
      setError('Error renderizando CV');
    }
  };

  return (
    <div style={{ maxWidth: '500px', margin: '0 auto', padding: '20px' }}>
      <h1>📄 Extrae tu CV del PDF</h1>

      {!preview ? (
        <div>
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileUpload}
            disabled={loading}
            style={{
              padding: '10px',
              border: '2px solid #007bff',
              borderRadius: '4px',
              width: '100%'
            }}
          />
          {loading && <p>⏳ Extrayendo datos del PDF... (~5 segundos)</p>}
          {error && <p style={{ color: 'red' }}>❌ {error}</p>}
        </div>
      ) : extractedData ? (
        <div>
          <h2>✅ Datos Extraídos</h2>

          <div style={{ background: '#f5f5f5', padding: '15px', borderRadius: '4px' }}>
            <h3>Información Personal</h3>
            <p><strong>Nombre:</strong> {extractedData.extracted_data.name}</p>
            <p><strong>Email:</strong> {extractedData.extracted_data.email}</p>
            <p><strong>Teléfono:</strong> {extractedData.extracted_data.phone}</p>
            <p><strong>Ubicación:</strong> {extractedData.extracted_data.location}</p>

            {extractedData.extracted_data.experience.length > 0 && (
              <div>
                <h3>Experiencia</h3>
                {extractedData.extracted_data.experience.map((exp, idx) => (
                  <p key={idx}>
                    <strong>{exp.company}</strong> - {exp.position}
                  </p>
                ))}
              </div>
            )}

            {extractedData.extracted_data.skills.length > 0 && (
              <div>
                <h3>Habilidades</h3>
                <p>{extractedData.extracted_data.skills.join(', ')}</p>
              </div>
            )}

            <p>
              <strong>Confianza:</strong> {extractedData.confidence_score}%
            </p>
          </div>

          <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
            <button
              onClick={() => handleRenderCV(extractedData)}
              style={{
                padding: '10px 20px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              📥 Descargar CV
            </button>
            <button
              onClick={() => setPreview(false)}
              style={{
                padding: '10px 20px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              ↩️ Subir otro
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
```

---

## ✅ Validación en Frontend

### Función Helper: Validar PDF antes de enviar

```javascript
function validatePDF(file) {
  const errors = [];

  // Validar que sea PDF
  if (file.type !== 'application/pdf') {
    errors.push('❌ Debe ser un archivo PDF');
  }

  // Validar tamaño (máximo 10MB)
  const maxSize = 10 * 1024 * 1024; // 10MB
  if (file.size > maxSize) {
    errors.push(`❌ PDF muy grande (máximo 10MB, tienes ${(file.size / 1024 / 1024).toFixed(2)}MB)`);
  }

  // Validar tamaño mínimo (al menos 50KB)
  if (file.size < 50 * 1024) {
    errors.push('❌ PDF muy pequeño (mínimo 50KB)');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

// Uso:
const file = document.getElementById('pdfInput').files[0];
const validation = validatePDF(file);

if (!validation.valid) {
  console.error('Errores de validación:');
  validation.errors.forEach(err => console.error(err));
  return;
}

// Si llegamos aquí, el PDF es válido
await extractCVFromPDF(file);
```

---

## 🎯 Casos de Uso

### 1. Usuario quiere actualizar su CV existente

```
Usuario → Carga PDF antiguo
        → Backend extrae datos
        → Frontend muestra vista previa
        → Usuario edita campos
        → Usuario genera nuevo CV con cambios
```

### 2. Usuario quiere convertir PDF a formato digital

```
Usuario → Carga PDF en papel (escaneado)
        → Backend realiza OCR
        → Backend estructura datos
        → Frontend genera YAML
        → Usuario puede editar y compartir
```

### 3. Integración con ESCO (futuro)

```
Usuario → Carga PDF
        → Backend extrae "Desarrollador Java"
        → Frontend: "¿Buscar en ESCO para autocompletar?"
        → Si: Busca "Desarrollador Java" en ESCO
        → Completa habilidades automáticamente
        → Usuario genera CV mejorado
```

---

## 🆘 Troubleshooting

### Error: "No text extracted from PDF"

**Causa:** El PDF es escaneado como imagen (no tiene texto embebido)

**Soluciones:**
1. OCR con Tesseract en backend (futuro)
2. Pedir al usuario un PDF de texto (no escaneado)
3. Usar Vision AI (Google Cloud) para OCR de imágenes

```javascript
// Detectar si PDF es imagen
async function isPDFScanned(pdfBase64) {
  // Enviar preview para ver OCR result
  const response = await axios.post('/api/v1/ocr/extract-cv-preview', {
    pdf_base64: pdfBase64,
    language: 'es'
  });
  
  return response.data.ocr_text.length < 100; // Si muy poco texto, es scaneado
}
```

---

### Error: "Extraction timeout"

**Causa:** PDF muy grande o conexión lenta

**Soluciones:**
1. Reducir tamaño del PDF (comprimir antes de enviar)
2. Usar `/extract-cv-preview` primero (más rápido)
3. Aumentar timeout en frontend

```javascript
const timeoutMs = 30000; // 30 segundos

Promise.race([
  extractCVFromPDF(file),
  new Promise((_, reject) => 
    setTimeout(() => reject(new Error('Timeout')), timeoutMs)
  )
]).catch(err => {
  if (err.message === 'Timeout') {
    console.error('Extracción tardó demasiado');
  }
});
```

---

### Error: "Extracted data incomplete"

**Causa:** OCR no reconoció bien el PDF (fuente extraña, baja calidad)

**Soluciones:**
1. Verificar que PDF sea legible
2. Aumentar `use_gemini: true` para mejor estructuración
3. Usuario completa campos manualmente
4. Guardar su CV como plantilla base

```javascript
async function improveExtraction(extractedData) {
  // Pedir al usuario que corrija
  const corrected = await showEditForm(extractedData);
  
  // Guardar como plantilla para futuros usos
  localStorage.setItem('cv_template', JSON.stringify(corrected));
  
  return corrected;
}
```

---

## 📊 Flujo Completo (Recomendado)

```javascript
async function completeOCRWorkflow(pdfFile) {
  const steps = [];

  // Step 1: Validar PDF
  const validation = validatePDF(pdfFile);
  if (!validation.valid) {
    steps.push({ status: 'error', message: validation.errors.join('\n') });
    return steps;
  }
  steps.push({ status: 'success', message: 'PDF validado ✅' });

  // Step 2: Convertir a base64
  const base64 = await fileToBase64(pdfFile);
  steps.push({ status: 'success', message: 'PDF convertido ✅' });

  // Step 3: Hacer OCR preview (rápido)
  const preview = await extractCVPreview(base64);
  if (!preview.extracted_data.name) {
    steps.push({ status: 'warning', message: 'No se detectó nombre, OCR incompleto' });
  }
  steps.push({ status: 'success', message: 'OCR extrae datos (preview) ✅' });

  // Step 4: Hacer OCR completo (con Gemini)
  const full = await extractCVFull(base64);
  steps.push({ status: 'success', message: 'OCR estructurado con IA ✅' });

  // Step 5: Generar CV
  const cv = await generateCV(full.suggested_cv_document);
  steps.push({ status: 'success', message: 'CV generado y listo ✅' });

  return {
    steps,
    extracted_data: full.extracted_data,
    cv_document: full.suggested_cv_document,
    pdf_base64: cv.pdf_base64
  };
}
```

---

## 🚀 Próximos Pasos (Roadmap)

- [ ] Integrar Gemini para mejor estructuración
- [ ] Soporte para escaneos de baja calidad (Tesseract)
- [ ] Detectar automáticamente idioma del CV
- [ ] Validar teléfono/email según país
- [ ] Extraer logos/imágenes de empresa
- [ ] Sugerir skills basado en ESCO
- [ ] Guardar plantillas de usuario
- [ ] Historial de extracciones

---

**¡Listo! El OCR está integrado. Ahora el frontend puede subir PDFs y extraer datos automáticamente.** 🎉
