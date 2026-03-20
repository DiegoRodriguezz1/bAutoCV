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

        # Generate only PDF, skip intermediate files for speed.
        def _build_render_cmd(executable: str, quiet: bool) -> list[str]:
            cmd_args = [
                executable,
                "render",
                "--dont-generate-markdown",
                "--dont-generate-html",
                "--dont-generate-png",
            ]
            if quiet:
                cmd_args.insert(2, "--quiet")
            cmd_args.append(str(input_file))
            return cmd_args

        cmd = _build_render_cmd(self.rendercv_bin, quiet=True)
        process_env = os.environ.copy()
        process_env["PYTHONUTF8"] = "1"
        process_env["PYTHONIOENCODING"] = "utf-8"

        try:
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
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
            ]
            cmd.extend(_build_render_cmd("", quiet=True)[1:])
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                env=process_env,
            )

        if process.returncode != 0:
            stderr_msg = process.stderr.strip() if process.stderr else ""
            stdout_msg = process.stdout.strip() if process.stdout else ""
            message = stderr_msg or stdout_msg or "Unknown RenderCV error"

            # RenderCV with --quiet can suppress validation details; retry once without it.
            if message == "Unknown RenderCV error":
                verbose_cmd = cmd.copy()
                if "--quiet" in verbose_cmd:
                    verbose_cmd.remove("--quiet")
                verbose_process = await asyncio.to_thread(
                    subprocess.run,
                    verbose_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    env=process_env,
                )
                verbose_stderr = verbose_process.stderr.strip() if verbose_process.stderr else ""
                verbose_stdout = verbose_process.stdout.strip() if verbose_process.stdout else ""
                verbose_message = verbose_stderr or verbose_stdout
                if verbose_message:
                    message = verbose_message

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
            cv_data = payload.cv.model_dump(exclude_none=True)

            # RenderCV validates email/phone formats; drop empty-string placeholders.
            for key in ("email", "phone", "website", "headline", "location", "photo"):
                value = cv_data.get(key)
                if isinstance(value, str) and not value.strip():
                    cv_data.pop(key, None)
                elif isinstance(value, list):
                    filtered = [item for item in value if not (isinstance(item, str) and not item.strip())]
                    if filtered:
                        cv_data[key] = filtered
                    else:
                        cv_data.pop(key, None)

            # Validate and sanitize email field
            email = cv_data.get("email")
            if isinstance(email, str):
                email = email.strip()
                if email and not _is_valid_email(email):
                    cv_data.pop("email", None)
                elif email:
                    cv_data["email"] = email

            # Validate and sanitize phone field
            phone = cv_data.get("phone")
            if isinstance(phone, str):
                phone = phone.strip()
                if phone and not _is_valid_phone(phone):
                    cv_data.pop("phone", None)
                elif phone:
                    cv_data["phone"] = phone

            # Trim whitespace from optional string fields to avoid RenderCV validation issues
            for key in ("headline", "location", "website"):
                value = cv_data.get(key)
                if isinstance(value, str):
                    trimmed = value.strip()
                    if trimmed:
                        cv_data[key] = trimmed
                    else:
                        cv_data.pop(key, None)

            document["cv"] = cv_data
        if payload.design:
            # mode="json" converts Enum values to plain strings for YAML serialization.
            document["design"] = payload.design.model_dump(mode="json", exclude_none=True)
        if payload.locale:
            document["locale"] = payload.locale
        if payload.settings:
            document["settings"] = payload.settings
        return document


def _is_valid_email(email: str) -> bool:
    """Check if email looks valid (basic: has @ and domain)."""
    if "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return False
    local, domain = parts
    # Domain must have at least one dot and a 2+ letter TLD
    if "." not in domain:
        return False
    domain_parts = domain.split(".")
    if len(domain_parts[-1]) < 2:
        return False
    return True


def _is_valid_phone(phone: str) -> bool:
    """Check if phone looks valid (basic: has at least 7 digits when stripped of non-digits)."""
    digits = "".join(c for c in phone if c.isdigit())
    return len(digits) >= 7
