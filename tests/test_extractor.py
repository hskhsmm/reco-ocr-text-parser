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


class TestClientNameExtraction:
    """거래처/고객사 추출 로직을 검증합니다."""

    def test_client_from_거래처_with_spaces(self, extractor):
        """OCR 공백이 포함된 '거 래 처:' 라벨에서 추출"""
        text = "거 래 처: 곰욕환경폐기물"
        result = extractor.extract(text)
        # 도메인 교정: 곰욕환경폐기물 → 고요환경
        assert result['client_name'] == "고요환경"

    def test_client_from_상호_with_spaces(self, extractor):
        """OCR 공백이 포함된 '상 호:' 라벨에서 추출"""
        text = "상 호: 고요환경"
        result = extractor.extract(text)
        assert result['client_name'] == "고요환경"

    def test_client_from_귀하_pattern(self, extractor):
        """'XXX 귀하' 패턴에서 고객사명 추출"""
        text = "신성(푸디스트) 귀하"
        result = extractor.extract(text)
        assert result['client_name'] == "신성(푸디스트)"

    def test_empty_client_returns_na(self, extractor):
        """거래처 값이 비어있으면 N/A"""
        text = "회 사 명 :\n총중량: 10000 kg"
        result = extractor.extract(text)
        assert result['client_name'] == "N/A"


class TestIssuerExtraction:
    """발급 회사명 및 주소 추출 로직을 검증합니다."""

    def test_issuer_with_주(self, extractor):
        """(주) 패턴 회사명 추출"""
        text = "동우바이오(주)\n2026-02-02 05:37:55"
        result = extractor.extract(text)
        assert result['issuer_name'] == "동우바이오(주)"

    def test_issuer_spacing_normalized(self, extractor):
        """한글 사이 공백과 (주) 앞뒤 공백 제거"""
        text = "(주) 하 은 펄 프\n경기도 화성시 팔탄면 포승향남로 2960-19"
        result = extractor.extract(text)
        assert result['issuer_name'] == "(주)하은펄프"

    def test_issuer_not_confused_with_client(self, extractor):
        """'귀하' 포함 줄은 issuer가 아닌 client로 분류"""
        text = "신성(푸디스트) 귀하\n정우리사이클링(주)"
        result = extractor.extract(text)
        assert result['issuer_name'] == "정우리사이클링(주)"
        assert result['client_name'] == "신성(푸디스트)"

    def test_issuer_address_extracted(self, extractor):
        """회사 주소 추출"""
        text = "(주)하은펄프\n경기도 화성시 팔탄면 포승향남로 2960-19"
        result = extractor.extract(text)
        assert result['issuer_address'] == "경기도 화성시 팔탄면 포승향남로 2960-19"

    def test_no_address_returns_na(self, extractor):
        """주소가 없으면 N/A"""
        text = "동우바이오(주)\n2026-02-02 05:37:55"
        result = extractor.extract(text)
        assert result['issuer_address'] == "N/A"
