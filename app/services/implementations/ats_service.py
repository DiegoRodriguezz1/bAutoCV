"""Puntaje ATS del prototipo: ATS = 25·S + 15·P + 15·H + 20·E + 10·C + 15·F (cada factor de 0 a 1)."""

import re

from app.schemas.experiment import AtsBreakdown, AtsResult, CvSnapshot

WEIGHTS = {"S": 25, "P": 15, "H": 15, "E": 20, "C": 10, "F": 15}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _filled(value: str) -> bool:
    return bool(value and value.strip())


def summary_factor(summary: str) -> float:
    words = len(summary.split())
    if 40 <= words <= 120:
        return 1.0
    if 20 <= words < 40:
        return 0.5
    return 0.0


def compute_ats(cv: CvSnapshot, esco_coverage_pct: float) -> AtsResult:
    skills = [skill for skill in cv.skills if _filled(skill)]
    sections = [
        _filled(cv.name) and _filled(cv.summary),
        any(_filled(item.degree) or _filled(item.institution) for item in cv.education),
        any(_filled(item.position) or _filled(item.company) for item in cv.experience),
        len(skills) > 0,
    ]
    phone_digits = re.sub(r"\D", "", cv.phone)

    breakdown = AtsBreakdown(
        S=sum(sections) / 4,
        P=summary_factor(cv.summary),
        H=min(len(skills), 5) / 5,
        E=max(0.0, min(esco_coverage_pct, 100.0)) / 100,
        C=(0.5 if EMAIL_PATTERN.match(cv.email.strip()) else 0) + (0.5 if len(phone_digits) >= 7 else 0),
        F=(0.5 if any(_filled(item.period) for item in cv.education) else 0)
        + (0.5 if any(_filled(item.period) for item in cv.experience) else 0),
    )
    score = sum(WEIGHTS[key] * value for key, value in breakdown.model_dump().items())
    return AtsResult(ats_score=round(score), ats_breakdown=breakdown)
