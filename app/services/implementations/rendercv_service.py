import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

from app.core.config import ROOT_DIR, get_settings
from app.schemas.cv import RenderCvRequest, RenderCvResponse
from app.services.interfaces.cv_renderer import CvRenderer


class RenderCvService(CvRenderer):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.output_dir = ROOT_DIR / self.settings.rendercv_output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rendercv_bin = self._resolve_rendercv_bin(self.settings.rendercv_bin)

    @staticmethod
    def _resolve_rendercv_bin(configured_bin: str) -> str:
        # Prefer configured value, but auto-detect venv binary on Windows/Linux.
        if Path(configured_bin).exists() or shutil.which(configured_bin):
            return configured_bin

        bin_name = "rendercv.exe" if os.name == "nt" else "rendercv"
        venv_candidate = Path(sys.executable).with_name(bin_name)
        if venv_candidate.exists():
            return str(venv_candidate)

        return configured_bin

    async def render(self, payload: RenderCvRequest) -> RenderCvResponse:
        if not self.settings.rendercv_enabled:
            return RenderCvResponse(
                accepted=False,
                message=(
                    "RenderCV is disabled. Set RENDERCV_ENABLED=true in your active .env "
                    f"(current APP_ENV={self.settings.app_env})."
                ),
            )

        file_stem = payload.output_name or f"cv_{uuid4().hex[:8]}"
        input_file = self.output_dir / f"{file_stem}.yaml"
        input_file.write_text(payload.profile_yaml, encoding="utf-8")

        cmd = [self.rendercv_bin, "render", str(input_file)]

        try:
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            # Fallback to module execution when CLI is not exposed in PATH.
            cmd = [sys.executable, "-m", "rendercv", "render", str(input_file)]
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

        if process.returncode != 0:
            message = process.stderr.strip() or process.stdout.strip() or "Unknown RenderCV error"
            return RenderCvResponse(
                accepted=False,
                message=f"RenderCV execution failed: {message}",
                output_path=str(input_file),
            )

        return RenderCvResponse(
            accepted=True,
            message="RenderCV execution completed. Verify generated files in output directory.",
            output_path=str(self.output_dir),
        )
