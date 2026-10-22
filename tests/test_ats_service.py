from app.schemas.experiment import CvSnapshot
from app.services.implementations.ats_service import compute_ats, summary_factor


def test_empty_cv_scores_zero():
    result = compute_ats(CvSnapshot(), 0)
    assert result.ats_score == 0
    assert result.ats_breakdown.S == 0


def test_full_cv_with_full_esco_coverage_scores_100(cv_snapshot):
    result = compute_ats(CvSnapshot(**cv_snapshot), 100)
    assert result.ats_score == 100
    assert result.ats_breakdown.model_dump() == {"S": 1, "P": 1, "H": 1, "E": 1, "C": 1, "F": 1}


def test_full_cv_without_esco_loses_20_points(cv_snapshot):
    assert compute_ats(CvSnapshot(**cv_snapshot), 0).ats_score == 80


def test_summary_word_bands():
    assert summary_factor(" ".join(["a"] * 19)) == 0
    assert summary_factor(" ".join(["a"] * 20)) == 0.5
    assert summary_factor(" ".join(["a"] * 39)) == 0.5
    assert summary_factor(" ".join(["a"] * 40)) == 1
    assert summary_factor(" ".join(["a"] * 120)) == 1
    assert summary_factor(" ".join(["a"] * 121)) == 0


def test_skills_capped_at_five(cv_snapshot):
    cv_snapshot["skills"] = ["s1", "s2", "s3"]
    assert compute_ats(CvSnapshot(**cv_snapshot), 0).ats_breakdown.H == 0.6
    cv_snapshot["skills"] = [f"s{i}" for i in range(9)]
    assert compute_ats(CvSnapshot(**cv_snapshot), 0).ats_breakdown.H == 1


def test_contact_and_period_halves(cv_snapshot):
    cv_snapshot["email"] = "no-es-correo"
    cv_snapshot["phone"] = "123"
    cv_snapshot["experience"][0]["period"] = ""
    breakdown = compute_ats(CvSnapshot(**cv_snapshot), 0).ats_breakdown
    assert breakdown.C == 0
    assert breakdown.F == 0.5


def test_coverage_is_clamped(cv_snapshot):
    assert compute_ats(CvSnapshot(**cv_snapshot), 250).ats_breakdown.E == 1
