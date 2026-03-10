from typing import Any

from pydantic import BaseModel, Field, model_validator


class CvSocialNetwork(BaseModel):
    network: str
    username: str


class CvData(BaseModel):
    name: str = Field(..., description="Full name")
    headline: str | None = None
    location: str | None = None
    email: str | None = None
    photo: str | None = None
    phone: str | None = None
    website: str | None = None
    social_networks: list[CvSocialNetwork] = Field(default_factory=list)
    custom_connections: list[dict[str, Any]] | None = None
    sections: dict[str, Any] = Field(default_factory=dict)


class RenderCvRequest(BaseModel):
    profile_yaml: str | None = Field(
        default=None,
        description="RenderCV YAML input",
    )
    cv: CvData | None = Field(
        default=None,
        description="Structured CV payload; converted to RenderCV YAML under 'cv'.",
    )
    design: dict[str, Any] | None = Field(
        default=None,
        description="RenderCV design configuration (theme, colors, typography, etc.)",
    )
    locale: dict[str, Any] | None = Field(
        default=None,
        description="RenderCV locale configuration (language, date format, translations)",
    )
    settings: dict[str, Any] | None = Field(
        default=None,
        description="RenderCV settings (current_date, etc.)",
    )
    output_name: str | None = Field(default=None, description="Optional output base name")

    @model_validator(mode="after")
    def validate_payload(self) -> "RenderCvRequest":
        if not self.profile_yaml and not self.cv:
            raise ValueError("Provide either 'profile_yaml' or 'cv'.")
        return self


class RenderCvResponse(BaseModel):
    accepted: bool
    message: str
    output_path: str | None = None
    pdf_base64: str | None = Field(
        default=None,
        description="Base64-encoded PDF file content",
    )
    filename: str | None = Field(
        default=None,
        description="Generated PDF filename",
    )
