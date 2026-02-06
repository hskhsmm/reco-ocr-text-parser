import re
from src.utils.formatter import merge_split_number_kg, is_noise_line
from src.parser.rules import (
    DATE_LABELS,
    CAR_LABELS,
    CAR_PART_HINTS,
    CLIENT_LABELS,
    ISSUER_HINTS,
)


def _contains_any(text: str, keywords):
    """문자열에 키워드 목록 중 하나라도 포함되는지 검사"""
    return any(k in text for k in keywords)


def _extract_after_label(label_norm: str, labels):
    """정규화된 한글 라벨 문자열에서 라벨 뒤 값을 추출"""
    for keyword in labels:
        if keyword in label_norm:
            val = label_norm.split(keyword, 1)[1].strip()
            if val:
                return val
            break
    return ""


class OcrExtractor:
    """
    OCR 텍스트에서 차량번호, 날짜, 중량(총중량, 공차, 실중량),
    발급회사(issuer), 거래처/고객사(client)를 추출하고 검증하는 클래스입니다.
    """

    # ── 내부 유틸 ──────────────────────────────────────────────
    @staticmethod
    def _remove_spaces_between_korean(text: str) -> str:
        """한글 글자 사이, 그리고 (주)/주식회사 뒤의 불필요한 공백을 제거합니다.
        예: '(주) 하 은 펄 프' → '(주)하은펄프'
            '거 래 처:' → '거래처:'
        """
        text = re.sub(r'(?<=[가-힣])\s(?=[가-힣])', '', text)
        text = re.sub(r'\s*\(주\)\s*', '(주)', text)
        return text

    # ── 내부: 중량 파서 ────────────────────────────────────────
    def _parse_weights(self, lines):
        """라인 목록에서 중량 관련 숫자를 추출하여 사전으로 반환.

        우선순위/매칭 규칙은 기존 extract의 로직을 그대로 따른다.
        반환: (weights_dict, temp_weight)
        """
        weights = {"total": 0, "empty": 0, "net": 0}
        temp_weight = 0

        for line in lines:
            line_lower = line.lower()
            val = 0

            # [우선순위 1] 'kg' 단위 숫자 추출
            kg_match = re.search(r'(\d+(?:,\d{3})*)\s*kg', line_lower)
            if kg_match:
                val = int(kg_match.group(1).replace(',', ''))
            else:
                # [우선순위 2] 줄 마지막 숫자 덩어리
                raw_nums = re.findall(r'(\d[\d,]+)', line_lower)
                if not raw_nums:
                    continue
                try:
                    val = int(raw_nums[-1].replace(',', ''))
                except (ValueError, IndexError):
                    continue

            if val == 0:
                continue

            # 공백 제거 후 키워드 매칭
            clean_line = line_lower.replace(" ", "")

            if any(k in clean_line for k in ["실중량", "순중량"]):
                if weights['net'] == 0:
                    weights['net'] = val
            elif any(k in clean_line for k in ["공차중량", "차중량"]):
                if weights['empty'] == 0:
                    weights['empty'] = val
            elif "총중량" in clean_line:
                if weights['total'] == 0:
                    weights['total'] = val
            elif '품명' in clean_line:
                if weights['total'] == 0:
                    weights['total'] = val
            elif '중량' in clean_line:
                if temp_weight == 0:
                    temp_weight = val

        return weights, temp_weight

    # ── 내부: 중량 산술 추론 ───────────────────────────────────
    @staticmethod
    def _infer_weights(w):
        """total/empty/net의 산술 일관성을 바탕으로 누락값을 추론.
        기존 동작 그대로 유지한다.
        """
        if w['total'] > 0 and w['empty'] > 0:
            calculated_net = w['total'] - w['empty']
            if calculated_net >= 0:
                w['net'] = calculated_net
        elif w['empty'] > 0 and w['net'] > 0 and w['total'] == 0:
            w['total'] = w['empty'] + w['net']
        elif w['total'] > 0 and w['net'] > 0 and w['empty'] == 0:
            calculated_empty = w['total'] - w['net']
            if calculated_empty >= 0:
                w['empty'] = calculated_empty
        return w

    # ── 메인 추출 ──────────────────────────────────────────────
    def extract(self, text: str) -> dict:
        results = {
            "car_number": "N/A",
            "date": "N/A",
            "issuer_name": "N/A",
            "issuer_address": "N/A",
            "client_name": "N/A",
            "weights": {"total": 0, "empty": 0, "net": 0}
        }

        # [전처리] 숫자 사이 공백 합치기 (예: "13 460 kg" → "13460kg")
        # 숫자와 'kg' 사이 공백으로 분리된 경우 병합 처리 (예: "13 460 kg" -> "13460kg")
        processed_text = merge_split_number_kg(text)
        lines = processed_text.split('\n')

        # ── 1단계: 메타데이터 추출 (날짜, 차량번호, 거래처/고객사) ──
        for line in lines:
            # 공백을 모두 제거한 검색용 문자열
            clean_kw = line.replace(" ", "")
            # 한글 사이 공백만 제거한 라벨 정규화 문자열
            label_norm = self._remove_spaces_between_korean(line).strip()

            # [날짜 추출]
            if any(k in clean_kw for k in DATE_LABELS) and results['date'] == "N/A":
                date_match = re.search(r'(\d{4}[-/.]\d{2}[-/.]\d{2})', line)
                if date_match:
                    results['date'] = date_match.group(1).replace('.', '-')
            # Fallback: 규칙 테이블 기반 라벨 매칭 (동작 불변, 동의어 추가만)
            if results['date'] == "N/A" and _contains_any(clean_kw, DATE_LABELS):
                dm = re.search(r'(\d{4}[-/.]\d{2}[-/.]\d{2})', line)
                if dm:
                    results['date'] = dm.group(1).replace('.', '-')

            # [차량번호 추출]
            if results['car_number'] == "N/A":
                if any(k in clean_kw for k in CAR_LABELS):
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if any(k in part for k in CAR_PART_HINTS):
                            # 콜론이 같은 토큰에 붙어있으면 다음 토큰이 값
                            if ':' in part or '.' in part:
                                if i + 1 < len(parts):
                                    # '입고' 같은 부가 키워드 제외
                                    val = parts[i + 1]
                                    if val not in ("입고", "출고"):
                                        results['car_number'] = val
                                        break
            # Fallback: 규칙 테이블 기반 라벨 매칭 (동작 불변, 동의어 추가만)
            if results['car_number'] == "N/A" and _contains_any(clean_kw, CAR_LABELS):
                parts = line.split()
                for i, part in enumerate(parts):
                    if _contains_any(part, CAR_PART_HINTS):
                        if ':' in part or '.' in part:
                            if i + 1 < len(parts):
                                val = parts[i + 1]
                                if val not in ("입고", "출고"):
                                    results['car_number'] = val
                                    break

            # [거래처/고객사 추출] - 라벨 기반
            if results['client_name'] == "N/A":
                # 한글 사이 공백이 제거된 label_norm에서 키워드 탐색
                for keyword in CLIENT_LABELS:
                    if keyword in label_norm:
                        val = label_norm.split(keyword, 1)[1].strip()
                        if val:
                            results['client_name'] = val
                        break
            # Fallback: 규칙 테이블 기반 라벨 매칭 (동작 불변, 동의어 추가만)
            if results['client_name'] == "N/A":
                val2 = _extract_after_label(label_norm, CLIENT_LABELS)
                if val2:
                    results['client_name'] = val2

            # [거래처/고객사 추출] - "XXX 귀하" 패턴
            if results['client_name'] == "N/A":
                guiha_match = re.search(r'^(.+?)\s+귀하\s*$', line.strip())
                if guiha_match:
                    results['client_name'] = guiha_match.group(1).strip()

        # ── 2단계: 중량 데이터 추출 ──
        w, temp_weight = self._parse_weights(lines)

        # 라벨 누락 값 보충 (동작 동일)
        if w['net'] > 0 and temp_weight > 0 and w['empty'] == 0:
            w['empty'] = temp_weight

        # ── 3단계: 무게 산술 검증 및 추론 ──
        w = self._infer_weights(w)
        results['weights'] = w

        # ── 4단계: 발급 회사명 추출 ──
        if results['issuer_name'] == "N/A":
            # 이미 추출된 값 집합 (중복 방지용)
            extracted_vals = {
                results['car_number'], results['date'], results['client_name']
            }

            # 4-1) '(주)', '주식회사' 패턴 탐색
            for line in lines:
                ls = line.strip()
                norm = self._remove_spaces_between_korean(ls)
                if _contains_any(norm, ISSUER_HINTS):
                    # 날짜/시간/무게/좌표 줄 제외
                    if re.search(r'^\d{4}[-/.]\d{2}[-/.]\d{2}', ls):
                        continue
                    if re.search(r'[\d,]+\s*kg', ls, re.IGNORECASE):
                        continue
                    if re.search(r'^\d{2,3}\.\d{5,}', ls):
                        continue
                    # 거래처(귀하 패턴)와 겹치지 않게
                    if norm.strip() in extracted_vals:
                        continue
                    if '귀하' in norm:
                        continue
                    results['issuer_name'] = norm
                    break

            # 4-2) 문서 하단 휴리스틱
            if results['issuer_name'] == "N/A":
                potential = []
                for line in lines[-5:]:
                    ls = line.strip()
                    if not ls:
                        continue
                    # 날짜/시간/좌표/순수숫자/무게(kg) 등 노이즈 라인은 제외
                    if is_noise_line(ls):
                        continue
                    if ls in extracted_vals:
                        continue
                    potential.append(ls)
                if potential:
                    results['issuer_name'] = self._remove_spaces_between_korean(
                        potential[-1]
                    )

        # ── 5단계: 발급 회사 주소 추출 ──
        # "경기도", "서울", "충청" 등 광역시/도로 시작하는 줄을 주소로 간주
        if results['issuer_address'] == "N/A":
            for line in lines:
                ls = line.strip()
                if re.match(
                    r'^(경기도|서울|부산|대구|인천|광주|대전|울산|세종|'
                    r'충청북도|충청남도|충북|충남|전라북도|전라남도|전북|전남|'
                    r'경상북도|경상남도|경북|경남|강원도|강원|제주도|제주)',
                    ls
                ):
                    results['issuer_address'] = ls
                    break

        return results
