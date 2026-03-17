from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CvSocialNetwork(BaseModel):
    network: str
    username: str


class CvCustomConnection(BaseModel):
    placeholder: str
    fontawesome_icon: str
    url: str | None = None


class CvBaseEntry(BaseModel):
    model_config = ConfigDict(extra="allow")


class CvDatedEntry(CvBaseEntry):
    date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    summary: str | None = None
    highlights: list[str] | None = None


class CvEducationEntry(CvDatedEntry):
    institution: str
    area: str
    degree: str | None = None


class CvExperienceEntry(CvDatedEntry):
    company: str
    position: str


class CvNormalEntry(CvDatedEntry):
    name: str


class CvOneLineEntry(CvBaseEntry):
    label: str
    details: str


class CvPublicationEntry(CvBaseEntry):
    title: str
    authors: list[str]
    doi: str | None = None
    url: str | None = None
    journal: str | None = None
    date: str | None = None


class CvBulletEntry(CvBaseEntry):
    bullet: str


class CvNumberedEntry(CvBaseEntry):
    number: str


class CvReversedNumberedEntry(CvBaseEntry):
    number: str


CvSectionEntry = (
    str
    | CvEducationEntry
    | CvExperienceEntry
    | CvNormalEntry
    | CvOneLineEntry
    | CvPublicationEntry
    | CvBulletEntry
    | CvNumberedEntry
    | CvReversedNumberedEntry
)


class CvData(BaseModel):
    name: str = Field(..., description="Full name")
    headline: str | None = None
    location: str | None = None
    email: str | list[str] | None = None
    photo: str | None = None
    phone: str | list[str] | None = None
    website: str | list[str] | None = None
    social_networks: list[CvSocialNetwork] = Field(default_factory=list)
    custom_connections: list[CvCustomConnection] | None = None
    sections: dict[str, list[CvSectionEntry]] = Field(default_factory=dict)


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
    generated_yaml: str | None = Field(
        default=None,
        description="RenderCV YAML generated from the structured payload or passed through from profile_yaml.",
    )
    pdf_base64: str | None = Field(
        default=None,
        description="Base64-encoded PDF file content",
    )
    filename: str | None = Field(
        default=None,
        description="Generated PDF filename",
    )


class RenderCvYamlResponse(BaseModel):
    generated_yaml: str = Field(..., description="RenderCV YAML document")
    document: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured document that was serialized to YAML.",
    )
