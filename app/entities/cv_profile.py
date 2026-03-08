from pydantic import BaseModel


class CvProfile(BaseModel):
    full_name: str
    email: str
    summary: str | None = None
