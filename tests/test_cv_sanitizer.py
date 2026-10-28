import pytest

from app.services.implementations.cv_sanitizer import (
    neutralize_typst,
    normalize_date,
    normalize_entry_dates,
    sanitize_text_fields,
)

WJ = "⁠"


class TestTypst:
    def test_hashtag_is_not_a_typst_command(self):
        assert neutralize_typst("Busco trabajo #remoto") == f"Busco trabajo #{WJ}remoto"

    def test_hash_before_non_letter_is_left_alone(self):
        assert neutralize_typst("C# y #1 del ranking") == "C# y #1 del ranking"

    def test_html_like_tags_are_kept_as_text(self):
        assert neutralize_typst("<b>negrita</b> y 3 < 5") == f"<{WJ}b>negrita<{WJ}/b> y 3 < 5"

    def test_double_dollar_is_not_math(self):
        assert neutralize_typst("Entre $$5 y $$10") == f"Entre ${WJ}$5 y ${WJ}$10"

    def test_contact_fields_are_not_touched(self):
        data = {"email": "a#b@c.co", "sections": {"Sobre mí": ["#hola"]}, "website": "https://x.co/#ancla"}
        result = sanitize_text_fields(data)
        assert result["email"] == "a#b@c.co"
        assert result["website"] == "https://x.co/#ancla"
        assert result["sections"]["Sobre mí"] == [f"#{WJ}hola"]


class TestDates:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2024", "2024"),
            ("2024-2", "2024-02"),
            ("2024/02", "2024-02"),
            ("2024-02-05", "2024-02-05"),
            ("02/2024", "2024-02"),
            ("enero 2024", "2024-01"),
            ("Sept. de 2023", "2023-09"),
            ("January 2022", "2022-01"),
            ("actual", "present"),
            ("Presente", "present"),
            ("present", "present"),
        ],
    )
    def test_readable_dates(self, raw, expected):
        assert normalize_date(raw) == expected

    @pytest.mark.parametrize("raw", ["ayer", "2024-13", "13/2024", "mes 2024", "", None])
    def test_unreadable_dates(self, raw):
        assert normalize_date(raw) is None

    def test_end_before_start_is_swapped(self):
        assert normalize_entry_dates({"start_date": "2025-06", "end_date": "2023-01"}) == {
            "start_date": "2023-01",
            "end_date": "2025-06",
        }

    def test_unreadable_dates_become_free_text(self):
        result = normalize_entry_dates({"company": "Acme", "start_date": "hace dos años", "end_date": "ayer"})
        assert result == {"company": "Acme", "date": "hace dos años – ayer"}

    def test_present_as_start_becomes_ongoing(self):
        assert normalize_entry_dates({"start_date": "actual", "end_date": "2021"}) == {
            "start_date": "2021",
            "end_date": "present",
        }

    def test_only_end_date_becomes_single_date(self):
        assert normalize_entry_dates({"end_date": "2020"}) == {"date": "2020"}

    def test_entries_without_dates_are_unchanged(self):
        entry = {"label": "Competencia técnica", "details": "Python"}
        assert normalize_entry_dates(entry) is entry
