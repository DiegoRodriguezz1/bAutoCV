from typing import Protocol

from app.schemas.cv import RenderCvRequest, RenderCvResponse


class CvRenderer(Protocol):
    async def render(self, payload: RenderCvRequest) -> RenderCvResponse:
        ...
