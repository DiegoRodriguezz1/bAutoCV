"""OCR service for extracting and structuring CV data from PDF files."""

import json
import re
from datetime import datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.ocr import (
    ExtractedCvData,
    OcrExtractRequest,
    OcrExtractResponse,
    OcrRawResult,
)


class OcrService:
    """Service for OCR extraction and CV data structuring."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.ocr_timeout = httpx.Timeout(self.settings.ocr_timeout_seconds)
        self.gemini_timeout = httpx.Timeout(self.settings.gemini_timeout_seconds)
        self.gemini_api_key = self.settings.gemini_api_key
        self.gemini_enabled = bool(self.gemini_api_key)

    async def extract_cv_from_pdf(
        self,
        request: OcrExtractRequest,
    ) -> OcrExtractResponse:
        """
        Extract CV data from PDF using OCR and optionally Gemini.

        Process:
        1. Send PDF to ocr.space API for text extraction
        2. Parse raw OCR text
        3. (Optional) Use Gemini to structure the data
        4. Generate RenderCV document
        """
        try:
            # Step 1: Extract text using OCR
            ocr_result = await self._extract_with_ocr(request.pdf_base64)

            if not ocr_result.text.strip():
                return OcrExtractResponse(
                    accepted=False,
                    message="OCR failed: No text extracted from PDF",
                    ocr_text="",
                )

            # Step 2: Extract data from OCR text
            if request.use_gemini and self.gemini_enabled:
                extracted = await self._structure_with_gemini(
                    ocr_result.text,
                    request.language,
                )
            else:
                extracted = self._structure_with_regex(
                    ocr_result.text,
                    request.language,
                )

            extracted.raw_text = ocr_result.text

            # Step 3: Generate RenderCV document
            cv_document = self._generate_cv_document(extracted)
            yaml_fragment = self._generate_yaml_fragment(extracted)

            return OcrExtractResponse(
                accepted=True,
                message="CV data extracted successfully",
                ocr_text=ocr_result.text,
                extracted_data=extracted,
                suggested_cv_document=cv_document,
                suggested_yaml=yaml_fragment,
                confidence_score=ocr_result.confidence,
            )

        except Exception as e:
            return OcrExtractResponse(
                accepted=False,
                message=f"Error during extraction: {str(e)}",
            )

    async def _extract_with_ocr(self, pdf_base64: str) -> OcrRawResult:
        """Call ocr.space API to extract text from PDF."""
        if not self.settings.ocr_space_api_key:
            raise ValueError(
                "OCR_SPACE_API_KEY is not configured. Set it in your active .env file."
            )

        async with httpx.AsyncClient(timeout=self.ocr_timeout) as client:
            response = await client.post(
                self.settings.ocr_space_endpoint,
                data={
                    "base64Image": f"data:application/pdf;base64,{pdf_base64}",
                    "apikey": self.settings.ocr_space_api_key,
                    "language": self.settings.ocr_default_language,
                    "isOverlayRequired": "true",
                },
            )
            response.raise_for_status()
            data = response.json()

            if data.get("IsErroredOnProcessing"):
                raise Exception(f"OCR Error: {data.get('ErrorMessage', 'Unknown error')}")

            parsed_results = data.get("ParsedResults", [])
            if not isinstance(parsed_results, list):
                parsed_results = []

            page_texts: list[str] = []
            confidence_values: list[float] = []

            for result in parsed_results:
                if not isinstance(result, dict):
                    continue
                parsed_text = result.get("ParsedText")
                if isinstance(parsed_text, str) and parsed_text.strip():
                    page_texts.append(parsed_text.strip())

                overlay = result.get("TextOverlay")
                if isinstance(overlay, dict):
                    lines = overlay.get("Lines", [])
                    if isinstance(lines, list):
                        for line in lines:
                            if not isinstance(line, dict):
                                continue
                            words = line.get("Words", [])
                            if not isinstance(words, list):
                                continue
                            for word in words:
                                if not isinstance(word, dict):
                                    continue
                                confidence = word.get("Confidence")
                                if isinstance(confidence, (int, float)):
                                    confidence_values.append(float(confidence))

            full_text = "\n\n".join(page_texts).strip()
            avg_confidence = (
                sum(confidence_values) / len(confidence_values)
                if confidence_values
                else (100.0 if full_text else 0.0)
            )

            return OcrRawResult(
                text=full_text,
                pages_count=len(page_texts),
                confidence=round(avg_confidence, 2),
                raw_response=data,
            )

    async def _structure_with_gemini(
        self,
        ocr_text: str,
        language: str,
    ) -> ExtractedCvData:
        """
        Use Google Gemini to parse and structure OCR text.

        Sends the raw OCR text to Gemini with instructions to extract:
        - Name
        - Email
        - Phone
        - Education
        - Experience
        - Skills
        """
        if not self.gemini_enabled:
            return self._structure_with_regex(ocr_text, language)

        prompt = (
            "You are a CV parser. Extract structured data from OCR text and return ONLY valid JSON.\n"
            "Required JSON shape:\n"
            "{\n"
            '  "name": string|null,\n'
            '  "email": string|null,\n'
            '  "phone": string|null,\n'
            '  "location": string|null,\n'
            '  "headline": string|null,\n'
            '  "summary": string|null,\n'
            '  "education": [{"institution": string, "area": string|null, "degree": string|null, "start_date": string|null, "end_date": string|null, "location": string|null, "highlights": string[] }],\n'
            '  "experience": [{"company": string, "position": string|null, "start_date": string|null, "end_date": string|null, "location": string|null, "summary": string|null, "highlights": string[] }],\n'
            '  "skills": string[]\n'
            "}\n"
            "Rules:\n"
            "- Preserve original language.\n"
            "- Use null when unknown.\n"
            "- Keep dates as found (YYYY-MM, YYYY-MM-DD, or present).\n"
            "- Do not include markdown fences.\n\n"
            f"OCR text (language hint: {language}):\n{ocr_text}"
        )

        url = (
            f"{self.settings.gemini_base_url.rstrip('/')}/models/"
            f"{self.settings.gemini_model}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.gemini_timeout) as client:
                response = await client.post(
                    url,
                    params={"key": self.gemini_api_key},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            raw_text = self._extract_gemini_text(data)
            raw_json = self._extract_json_payload(raw_text)
            parsed = json.loads(raw_json)

            return ExtractedCvData(
                name=parsed.get("name"),
                email=parsed.get("email"),
                phone=parsed.get("phone"),
                location=parsed.get("location"),
                headline=parsed.get("headline"),
                summary=parsed.get("summary"),
                education=parsed.get("education") if isinstance(parsed.get("education"), list) else [],
                experience=parsed.get("experience") if isinstance(parsed.get("experience"), list) else [],
                skills=[skill for skill in parsed.get("skills", []) if isinstance(skill, str)],
            )
        except Exception:
            # Fallback ensures OCR endpoint still works if Gemini fails.
            return self._structure_with_regex(ocr_text, language)

    @staticmethod
    def _extract_gemini_text(payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates", [])
        if not isinstance(candidates, list):
            return ""
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content")
            if not isinstance(content, dict):
                continue
            parts = content.get("parts", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        return text.strip()
        return ""

    @staticmethod
    def _extract_json_payload(text: str) -> str:
        if not text:
            return "{}"

        fenced = re.search(r"```json\s*(\{.*\})\s*```", text, re.DOTALL)
        if fenced:
            return fenced.group(1)

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return "{}"

    @staticmethod
    def _structure_with_regex(
        text: str,
        language: str,
    ) -> ExtractedCvData:
        """
        Parse OCR text using regex patterns.

        Extracts common patterns for:
        - Email: xxx@xxx.com
        - Phone: +XX XXX XXX XXX
        - Name: Usually first line(s)
        - Sections: Education, Experience, Skills
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Extract email
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(email_pattern, text)
        email = emails[0] if emails else None

        # Extract phone
        phone_pattern = r"(?:\+\d{1,3}[-.\s]?)?\(?\d{2,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
        phones = re.findall(phone_pattern, text)
        phone = phones[0] if phones else None

        # Extract name (usually first non-empty line or line before email)
        name = None
        for line in lines[:5]:
            if len(line) > 3 and len(line) < 100 and not any(
                char.isdigit() for char in line[:3]
            ):
                name = line
                break

        # Extract education section
        education = OcrService._extract_section(text, r"(?i)(education|educación|formación)")
        experience = OcrService._extract_section(text, r"(?i)(experience|experiencia|work)")
        skills = OcrService._extract_skills(text)

        return ExtractedCvData(
            name=name,
            email=email,
            phone=phone,
            education=education,
            experience=experience,
            skills=skills,
        )

    @staticmethod
    def _extract_section(text: str, pattern: str) -> list[dict]:
        """Extract a section from CV text (e.g., Education, Experience)."""
        # Simple heuristic: find the section header, then extract lines until next header
        sections = []
        # This is a placeholder; could be enhanced with better parsing
        return sections

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        """Extract skills from CV text."""
        # Look for common skill patterns
        skill_section = re.search(
            r"(?i)(skills|competencias|habilidades|technical skills)[:\s]*(.*?)(?=\n\n|\n(?:education|experience|languages|$))",
            text,
            re.DOTALL,
        )

        skills = []
        if skill_section:
            skills_text = skill_section.group(2)
            # Split by comma, dash, or bullet point
            potential_skills = re.split(r"[,\-•\n]", skills_text)
            skills = [s.strip() for s in potential_skills if s.strip() and len(s.strip()) > 2]

        return skills[:20]  # Limit to 20 skills

    @staticmethod
    def _generate_cv_document(extracted: ExtractedCvData) -> dict[str, Any]:
        """Generate a complete RenderCV document from extracted data."""
        return {
            "cv": {
                "name": extracted.name or "Your Name",
                "headline": extracted.headline or "Professional",
                "location": extracted.location,
                "email": extracted.email,
                "phone": extracted.phone,
                "sections": {
                    "Perfil profesional": [
                        extracted.summary or "Professional with experience"
                    ],
                    "Educación": extracted.education or [],
                    "Experiencia": extracted.experience or [],
                    "Habilidades": [
                        {"label": "Technical Skills", "details": ", ".join(extracted.skills[:10])}
                    ]
                    if extracted.skills
                    else [],
                },
            },
            "design": {"theme": "classic"},
            "locale": {"language": "spanish"},
            "settings": {"current_date": datetime.now().strftime("%Y-%m-%d")},
        }

    @staticmethod
    def _generate_yaml_fragment(extracted: ExtractedCvData) -> str:
        """Generate YAML fragment from extracted data."""
        yaml_lines = [
            "# Auto-generated from OCR extraction",
            f"name: {extracted.name or 'Your Name'}",
        ]

        if extracted.headline:
            yaml_lines.append(f"headline: {extracted.headline}")

        if extracted.location:
            yaml_lines.append(f"location: {extracted.location}")

        if extracted.email:
            yaml_lines.append(f"email: {extracted.email}")

        if extracted.phone:
            yaml_lines.append(f"phone: {extracted.phone}")

        yaml_lines.append("\nsections:")

        if extracted.experience:
            yaml_lines.append("  Experiencia:")
            for exp in extracted.experience[:3]:
                yaml_lines.append(f"    - empresa: {exp.get('company', 'Unknown')}")
                yaml_lines.append(f"      posición: {exp.get('position', 'Unknown')}")

        if extracted.education:
            yaml_lines.append("  Educación:")
            for edu in extracted.education[:2]:
                yaml_lines.append(f"    - institución: {edu.get('institution', 'Unknown')}")
                yaml_lines.append(f"      área: {edu.get('area', 'Unknown')}")

        if extracted.skills:
            yaml_lines.append("  Habilidades:")
            for skill in extracted.skills[:5]:
                yaml_lines.append(f"    - {skill}")

        return "\n".join(yaml_lines)
