#!/usr/bin/env python3
"""
Example: ESCO Integration Workflow for CV Building

This script demonstrates the complete flow:
1. Search for occupations (autocomplete)
2. Load occupation + essential/optional skills
3. Generate a professional summary and YAML fragment
4. (Optionally) Render the CV to PDF

Usage:
    python examples/esco_workflow.py
"""

import asyncio
import json
from typing import Any

import httpx


# ============================================================================
# Configuration
# ============================================================================

API_BASE = "http://localhost:8000/api/v1"
LANGUAGE = "es"


# ============================================================================
# Helper Functions
# ============================================================================


async def search_occupations(text: str, limit: int = 5) -> dict[str, Any]:
    """Search for occupations using fast autocomplete."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/esco/occupations/suggest",
            params={
                "text": text,
                "language": LANGUAGE,
                "limit": limit,
            },
        )
        response.raise_for_status()
        return response.json()


async def load_occupation_skills(
    occupation_uri: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Load occupation + essential/optional skills."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/esco/occupations/skills",
            params={
                "occupation_uri": occupation_uri,
                "language": LANGUAGE,
                "limit": limit,
            },
        )
        response.raise_for_status()
        return response.json()


async def generate_description_assistant(
    occupation_uri: str,
    selected_skill_uris: list[str],
    additional_context: list[str] | None = None,
) -> dict[str, Any]:
    """Build professional summary + YAML fragment from ESCO data."""
    async with httpx.AsyncClient() as client:
        payload = {
            "occupation_uri": occupation_uri,
            "selected_skill_uris": selected_skill_uris,
            "language": LANGUAGE,
            "additional_context": additional_context or [],
            "skill_limit": 12,
        }
        response = await client.post(
            f"{API_BASE}/esco/occupations/description-assistant",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def generate_rendercv_yaml(profile_yaml: str) -> dict[str, Any]:
    """Generate RenderCV YAML (without rendering PDF)."""
    async with httpx.AsyncClient() as client:
        payload = {"profile_yaml": profile_yaml}
        response = await client.post(
            f"{API_BASE}/cv/yaml",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


async def render_cv(profile_yaml: str) -> dict[str, Any]:
    """Render CV to PDF."""
    async with httpx.AsyncClient() as client:
        payload = {"profile_yaml": profile_yaml}
        response = await client.post(
            f"{API_BASE}/cv/render",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# Main Workflow
# ============================================================================


async def main():
    print("=" * 70)
    print("ESCO CV Assistant Workflow Example")
    print("=" * 70)

    # Step 1: Search for occupation
    print("\n[1] Searching for occupations matching 'desarrollador java'...")
    occupation_results = await search_occupations("desarrollador java", limit=3)
    print(f"Found {occupation_results['total']} occupations.")

    if not occupation_results["occupations"]:
        print("No occupations found. Exiting.")
        return

    # Display results and select first one
    print("\nOccupations:")
    for i, occ in enumerate(occupation_results["occupations"], 1):
        print(f"  {i}. {occ['title']} ({occ['code']})")

    selected_occupation = occupation_results["occupations"][0]
    print(f"\n→ Selected: {selected_occupation['title']}")

    # Step 2: Load skills for the occupation
    print("\n[2] Loading essential and optional skills...")
    skills_bundle = await load_occupation_skills(
        selected_occupation["uri"],
        limit=10,
    )

    essential = skills_bundle["essential_skills"]
    optional = skills_bundle["optional_skills"]

    print(f"Essential skills ({len(essential)}):")
    for skill in essential[:5]:
        print(f"  - {skill['title']}")
    if len(essential) > 5:
        print(f"  ... and {len(essential) - 5} more")

    print(f"\nOptional skills ({len(optional)}):")
    for skill in optional[:3]:
        print(f"  - {skill['title']}")
    if len(optional) > 3:
        print(f"  ... and {len(optional) - 3} more")

    # Step 3: Build description assistant payload
    print("\n[3] Generating professional summary and CV patch...")

    # Select top 5 essential skills
    selected_skill_uris = [skill["uri"] for skill in essential[:5]]

    assistant_response = await generate_description_assistant(
        selected_occupation["uri"],
        selected_skill_uris,
        additional_context=[
            "8 años de experiencia en desarrollo",
            "Especializado en arquitectura de microservicios",
            "Mentor en equipos de ingeniería",
        ],
    )

    print(f"\nSuggested Headline:\n  {assistant_response['suggested_headline']}")
    print(f"\nSuggested Summary (truncated):\n  {assistant_response['suggested_summary'][:200]}...")
    print(f"\nSuggested Highlights ({len(assistant_response['suggested_highlights'])} bullets):")
    for bullet in assistant_response["suggested_highlights"][:3]:
        print(f"  • {bullet}")

    # Show the YAML snippet
    print("\n[4] Generated YAML Fragment (ready to paste):")
    print("---")
    print(assistant_response["suggested_yaml_fragment"])
    print("---")

    # Step 4: Demonstrate full CV generation
    print("\n[5] Generating full CV YAML from template...")

    base_yaml = f"""
cv:
  name: Juan Pérez García
  headline: {assistant_response['suggested_headline']}
  location: Madrid, España
  email: juan@example.com
  phone: "+34 600 123 456"
  website: https://github.com/juanperez
  social_networks:
    - network: GitHub
      username: juanperez
    - network: LinkedIn
      username: juanperezgarcia

  sections:
    {assistant_response['suggested_yaml_fragment'].replace('headline:', '').lstrip()}

design:
  theme: classic

locale:
  language: spanish
""".strip()

    yaml_response = await generate_rendercv_yaml(base_yaml)
    print(f"Generated YAML length: {len(yaml_response['generated_yaml'])} chars")

    print("\n[6] Rendering CV to PDF...")
    render_response = await render_cv(base_yaml)

    if render_response["accepted"]:
        print(f"✓ PDF generated successfully!")
        print(f"  Output: {render_response['output_path']}")
        print(f"  File: {render_response['filename']}")
    else:
        print(f"✗ Failed to render: {render_response['message']}")

    print("\n" + "=" * 70)
    print("Workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
