from pydantic import BaseModel, Field, field_validator

from app.schemas.experiment import UtcDatetime


class SavedCvWrite(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    yaml_content: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío")
        return value


class SavedCvSummary(BaseModel):
    id: int
    name: str
    updated_at: UtcDatetime


class SavedCvResponse(SavedCvSummary):
    yaml_content: str
    created_at: UtcDatetime
