from pydantic import BaseModel, Field


class OcrExtractRequest(BaseModel):
    """Request to extract CV data from PDF using OCR."""
    
    pdf_base64: str = Field(
        ...,
        description="PDF file content in base64 encoding"
    )
    language: str = Field(
        default="es",
        description="Language code for OCR (es, en, etc.)"
    )
    use_gemini: bool = Field(
        default=True,
        description="If True, use Gemini AI to structure the OCR output"
    )


class OcrRawResult(BaseModel):
    """Raw OCR output from ocr.space API."""
    
    text: str = Field(..., description="Extracted text from PDF")
    pages_count: int = Field(..., description="Number of pages in PDF")
    confidence: float = Field(
        default=0.0,
        description="OCR confidence score (0-100)"
    )
    raw_response: dict = Field(
        default_factory=dict,
        description="Full response from ocr.space API"
    )


class ExtractedCvData(BaseModel):
    """Structured CV data extracted from PDF."""
    
    name: str | None = Field(default=None, description="Person's full name")
    email: str | None = Field(default=None, description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    location: str | None = Field(default=None, description="Location/City")
    headline: str | None = Field(default=None, description="Professional headline")
    summary: str | None = Field(default=None, description="Professional summary")
    
    education: list[dict] = Field(
        default_factory=list,
        description="List of education entries"
    )
    experience: list[dict] = Field(
        default_factory=list,
        description="List of work experience entries"
    )
    skills: list[str] = Field(
        default_factory=list,
        description="List of skills"
    )
    
    raw_text: str | None = Field(
        default=None,
        description="Original OCR text (for reference)"
    )


class OcrExtractResponse(BaseModel):
    """Response from OCR extraction endpoint."""
    
    accepted: bool
    message: str
    ocr_text: str | None = Field(
        default=None,
        description="Raw OCR extracted text"
    )
    extracted_data: ExtractedCvData | None = Field(
        default=None,
        description="Structured CV data"
    )
    suggested_cv_document: dict | None = Field(
        default=None,
        description="Complete RenderCV document ready to use"
    )
    suggested_yaml: str | None = Field(
        default=None,
        description="Generated YAML fragment ready to paste"
    )
    confidence_score: float = Field(
        default=0.0,
        description="Overall extraction confidence"
    )
