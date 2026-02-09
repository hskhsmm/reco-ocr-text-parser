import pytest
from src.parser.cleaner import clean_text


class TestCleanText:
    """clean_text 함수의 텍스트 정제 로직을 검증합니다."""

    def test_empty_input(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_remove_asterisks(self):
        assert "***" not in clean_text("*** 계근표 ***")

    def test_fix_ocr_typo_계그표(self):
        result = clean_text("계 그 표")
        assert "계근표" in result

    def test_fix_ocr_typo_품종명랑(self):
        result = clean_text("품종명랑 식물")
        assert "품명" in result

    def test_fix_duplicate_입고(self):
        result = clean_text("입 고입고")
        assert result == "입고"

    def test_remove_noise_text(self):
        result = clean_text("공육을 unle 테스트")
        assert "공육을 unle" not in result

    def test_normalize_whitespace(self):
        result = clean_text("총중량:    13460   kg")
        assert "  " not in result

    def test_label_spacing_normalization(self):
        result = clean_text("날 짜: 2026-02-02")
        assert "날짜" in result
