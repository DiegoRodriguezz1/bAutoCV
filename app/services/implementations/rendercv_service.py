import asyncio
import base64
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from uuid import uuid4

import yaml

from app.core.config import ROOT_DIR, get_settings
from app.schemas.cv import RenderCvRequest, RenderCvResponse, RenderCvYamlResponse
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
        yaml_response = self.generate_yaml(payload)
        yaml_content = yaml_response.generated_yaml

        if not yaml_content:
            return RenderCvResponse(
                accepted=False,
                message="No CV content provided. Send 'profile_yaml' or 'cv'.",
            )

        input_file.write_text(yaml_content, encoding="utf-8")

        # Clean previous rendercv_output folder to avoid conflicts
        rendercv_output_dir = self.output_dir / "rendercv_output"
        if rendercv_output_dir.exists():
            shutil.rmtree(rendercv_output_dir, ignore_errors=True)

        # Generate only PDF, skip intermediate files for speed
        cmd = [
            self.rendercv_bin,
            "render",
            "--quiet",
            "--dont-generate-markdown",
            "--dont-generate-html",
            "--dont-generate-png",
            str(input_file),
        ]
        process_env = os.environ.copy()
        process_env["PYTHONUTF8"] = "1"
        process_env["PYTHONIOENCODING"] = "utf-8"

        try:
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env=process_env,
            )
        except FileNotFoundError:
            # Fallback to module execution when CLI is not exposed in PATH.
            cmd = [
                sys.executable,
                "-X",
                "utf8",
                "-m",
                "rendercv",
                "render",
                "--quiet",
                "--dont-generate-markdown",
                "--dont-generate-html",
                "--dont-generate-png",
                str(input_file),
            ]
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env=process_env,
            )

        if process.returncode != 0:
            message = process.stderr.strip() or process.stdout.strip() or "Unknown RenderCV error"
            return RenderCvResponse(
                accepted=False,
                message=f"RenderCV execution failed: {message}",
                output_path=str(input_file.relative_to(ROOT_DIR)),
                generated_yaml=yaml_content,
            )

        # RenderCV generates files in rendercv_output/ subdirectory
        rendercv_output_dir = self.output_dir / "rendercv_output"
        
        # Find the generated PDF (RenderCV uses cv.name for filename, not input filename)
        pdf_files = list(rendercv_output_dir.glob("*.pdf")) if rendercv_output_dir.exists() else []
        
        if not pdf_files:
            return RenderCvResponse(
                accepted=False,
                message=f"No PDF found in rendercv_output. Check RenderCV output.",
                output_path=str(rendercv_output_dir.relative_to(ROOT_DIR)),
            )

        # Use the first (and should be only) PDF found
        generated_pdf = pdf_files[0]
        
        # Move PDF to output directory with desired name
        final_pdf_name = f"{file_stem}.pdf"
        final_pdf_path = self.output_dir / final_pdf_name
        
        # Remove old PDF if exists
        if final_pdf_path.exists():
            final_pdf_path.unlink()
        
        shutil.move(str(generated_pdf), str(final_pdf_path))

        # Read PDF and encode to base64
        pdf_bytes = final_pdf_path.read_bytes()
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Clean up temporary files
        try:
            input_file.unlink(missing_ok=True)
            # Remove entire rendercv_output directory
            if rendercv_output_dir.exists():
                shutil.rmtree(rendercv_output_dir, ignore_errors=True)
        except Exception:
            pass  # Non-critical cleanup

        # Return relative path instead of absolute system path
        relative_path = str(final_pdf_path.relative_to(ROOT_DIR))

        return RenderCvResponse(
            accepted=True,
            message="PDF generated successfully.",
            output_path=relative_path,
            generated_yaml=yaml_content,
            pdf_base64=pdf_base64,
            filename=final_pdf_name,
        )

    def generate_yaml(self, payload: RenderCvRequest) -> RenderCvYamlResponse:
        if payload.profile_yaml:
            try:
                document = yaml.safe_load(payload.profile_yaml) or {}
            except yaml.YAMLError:
                document = {}

            return RenderCvYamlResponse(
                generated_yaml=payload.profile_yaml,
                document=document if isinstance(document, dict) else {},
            )

        document = self._build_document(payload)
        generated_yaml = yaml.safe_dump(
            document,
            allow_unicode=True,
            sort_keys=False,
        )
        return RenderCvYamlResponse(generated_yaml=generated_yaml, document=document)

    @staticmethod
    def _build_document(payload: RenderCvRequest) -> dict[str, Any]:
        document: dict[str, Any] = {}
        if payload.cv is not None:
            document["cv"] = payload.cv.model_dump(exclude_none=True)
        if payload.design:
            document["design"] = payload.design
        if payload.locale:
            document["locale"] = payload.locale
        if payload.settings:
            document["settings"] = payload.settings
        return document
