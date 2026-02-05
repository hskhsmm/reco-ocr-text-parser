import pytest
from src.parser.extractor import OcrExtractor


@pytest.fixture
def extractor():
    return OcrExtractor()


class TestWeightExtraction:
    """중량 추출 및 산술 검증 로직을 검증합니다."""

    def test_basic_weight_with_kg(self, extractor):
        text = "총중량: 12480 kg\n차중량: 7470 kg\n실중량: 5010 kg"
        result = extractor.extract(text)
        assert result['weights']['total'] == 12480
        assert result['weights']['empty'] == 7470
        assert result['weights']['net'] == 5010

    def test_split_number_merge(self, extractor):
        """OCR이 숫자를 공백으로 분리한 경우 (예: '13 460 kg' → 13460)"""
        text = "총중량: 13 460 kg\n차중량: 7 560 kg\n실중량: 5 900 kg"
        result = extractor.extract(text)
        assert result['weights']['total'] == 13460
        assert result['weights']['empty'] == 7560
        assert result['weights']['net'] == 5900

    def test_weight_with_timestamp_noise(self, extractor):
        """시간값(02:07)이 섞여 있어도 무게만 정확히 추출"""
        text = "총중량: 02:07 13 460 kg\n차중량: 02 : 13 7 560 kg\n실중량: 5 900 kg"
        result = extractor.extract(text)
        assert result['weights']['total'] == 13460
        assert result['weights']['empty'] == 7560
        assert result['weights']['net'] == 5900

    def test_comma_formatted_weight(self, extractor):
        """콤마 포맷 숫자 (예: 13,460 kg)"""
        text = "총중량: 13,460 kg\n차중량: 7,560 kg\n실중량: 5,900 kg"
        result = extractor.extract(text)
        assert result['weights']['total'] == 13460
        assert result['weights']['empty'] == 7560

    def test_net_inference_from_total_and_empty(self, extractor):
        """총중량과 공차만 있을 때 실중량 자동 계산"""
        text = "총중량: 10000 kg\n차중량: 6000 kg"
        result = extractor.extract(text)
        assert result['weights']['net'] == 4000

    def test_total_inference_from_empty_and_net(self, extractor):
        """공차와 실중량만 있을 때 총중량 추론"""
        text = "차중량: 6000 kg\n실중량: 4000 kg"
        result = extractor.extract(text)
        assert result['weights']['total'] == 10000

    def test_empty_inference_from_total_and_net(self, extractor):
        """총중량과 실중량만 있을 때 공차 추론"""
        text = "총중량: 10000 kg\n실중량: 4000 kg"
        result = extractor.extract(text)
        assert result['weights']['empty'] == 6000

    def test_arithmetic_consistency(self, extractor):
        """total = empty + net 산술 관계 검증"""
        text = "총중량: 14080 kg\n차중량: 13950 kg\n실중량: 130 kg"
        result = extractor.extract(text)
        w = result['weights']
        assert w['total'] == w['empty'] + w['net']


class TestDateExtraction:
    """날짜 추출 및 정규화 로직을 검증합니다."""

    def test_date_with_hyphen(self, extractor):
        text = "날짜: 2026-02-02"
        result = extractor.extract(text)
        assert result['date'] == "2026-02-02"

    def test_date_with_dot(self, extractor):
        """마침표 구분자를 하이픈으로 정규화"""
        text = "계량일자: 2025.12.01"
        result = extractor.extract(text)
        assert result['date'] == "2025-12-01"

    def test_date_with_trailing_sequence(self, extractor):
        """날짜 뒤에 일련번호가 붙은 경우 (예: 2026-02-02-00004)"""
        text = "날짜: 2026-02-02-00004"
        result = extractor.extract(text)
        assert result['date'] == "2026-02-02"

    def test_no_date_returns_na(self, extractor):
        text = "총중량: 10000 kg"
        result = extractor.extract(text)
        assert result['date'] == "N/A"


class TestCarNumberExtraction:
    """차량번호 추출 로직을 검증합니다."""

    def test_car_number_with_korean(self, extractor):
        text = "차번호: 80구8713"
        result = extractor.extract(text)
        assert result['car_number'] == "80구8713"

    def test_car_number_label_variant(self, extractor):
        text = "차량번호: 12가3456"
        result = extractor.extract(text)
        assert result['car_number'] == "12가3456"

    def test_no_car_number_returns_na(self, extractor):
        text = "총중량: 10000 kg"
        result = extractor.extract(text)
        assert result['car_number'] == "N/A"
