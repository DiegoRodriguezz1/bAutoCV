from pydantic import BaseModel, Field


class RenderCvRequest(BaseModel):
    profile_yaml: str = Field(..., description="RenderCV YAML input")
    output_name: str | None = Field(default=None, description="Optional output base name")


class RenderCvResponse(BaseModel):
    accepted: bool
    message: str
    output_path: str | None = None
