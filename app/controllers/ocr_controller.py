"""OCR Controller - Extract CV data from PDFs"""

from fastapi import APIRouter

from app.schemas.ocr import OcrExtractRequest, OcrExtractResponse
from app.services.implementations.ocr_service import OcrService

router = APIRouter(prefix="/ocr", tags=["OCR"])
ocr_service = OcrService()


@router.post("/extract-cv", response_model=OcrExtractResponse)
async def extract_cv_from_pdf(
    request: OcrExtractRequest,
) -> OcrExtractResponse:
    """
    Extract CV data from a PDF using OCR.

    Process:
    1. Extract text from PDF using ocr.space API
    2. (Optional) Structure with Gemini AI
    3. Generate RenderCV YAML document

    Request:
    ```json
    {
      "pdf_base64": "JVBERi0xLjQKJeLjz9MNCjEgMCBvYmpvPjwvVHlwZS9DYXR...",
      "language": "es",
      "use_gemini": true
    }
    ```

    Response includes:
    - `extracted_data`: Structured CV data
    - `suggested_cv_document`: Full RenderCV document
    - `suggested_yaml`: YAML fragment ready to paste
    - `ocr_text`: Raw OCR output
    """
    return await ocr_service.extract_cv_from_pdf(request)


@router.post("/extract-cv-preview")
async def preview_ocr_extraction(
    request: OcrExtractRequest,
) -> dict:
    """
    Quick preview of OCR extraction without Gemini processing.

    Useful for frontend to show user what was extracted before final processing.
    """
    response = await ocr_service.extract_cv_from_pdf(
        OcrExtractRequest(
            pdf_base64=request.pdf_base64,
            language=request.language,
            use_gemini=False,  # Force regex-only for speed
        )
    )
    return {
        "ocr_text": response.ocr_text,
        "extracted_data": response.extracted_data,
        "confidence_score": response.confidence_score,
    }
