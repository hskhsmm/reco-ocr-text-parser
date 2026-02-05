import re

class OcrExtractor:
    """
    OCR 텍스트에서 차량번호, 날짜, 중량(총중량, 공차, 실중량)을 추출하고 검증하는 클래스입니다.
    비정형 데이터의 노이즈와 라벨 누락에 대응하는 견고한 파싱 로직을 제공합니다.
    """
    def extract(self, text: str) -> dict:
        # 최종 결과물 스키마 초기화
        results = {
            "car_number": "N/A",
            "date": "N/A",
            "weights": {"total": 0, "empty": 0, "net": 0}
        }
        
        # [Strategy 1] OCR 노이즈 선제거 (Preprocessing)
        # sample_02처럼 숫자 사이에 공백이 생겨 값이 끊기는 현상(예: "13 460 kg")을 해결합니다.
        # '숫자-공백-숫자-kg' 패턴을 찾아 공백을 제거하고 하나의 숫자로 통합합니다.
        processed_text = re.sub(r'(\d+)\s+(\d+)\s*kg', r'\1\2kg', text)
        lines = processed_text.split('\n')
        
        # 1단계: 메타데이터(날짜 및 차량번호) 추출
        for line in lines:
            # 키워드 매칭률을 높이기 위해 줄 내부 공백을 제거한 검색용 문자열 생성
            clean_line_for_keyword = line.replace(" ", "")
            
            # [날짜 추출] YYYY-MM-DD 또는 YYYY.MM.DD 형식 모두 대응
            if any(k in clean_line_for_keyword for k in ["계량일자", "날짜", "일시"]) and results['date'] == "N/A":
                date_match = re.search(r'(\d{4}[-/.]\d{2}[-/.]\d{2})', line)
                if date_match:
                    # 마침표(.)를 하이픈(-)으로 통일하여 데이터 규격 정규화 수행
                    results['date'] = date_match.group(1).replace('.', '-')

            # [차량번호 추출] 다양한 라벨(차량번호, 차번호, No.) 뒤에 오는 단어를 획득
            if any(k in clean_line_for_keyword for k in ["차량번호:", "차번호:", "차량No."]) and results['car_number'] == "N/A":
                parts = line.split()
                for i, part in enumerate(parts):
                    # 키워드(번호/No.)가 포함된 단어의 바로 다음 index 값을 차량번호로 간주
                    if any(k in part for k in ["번호", "No."]):
                        if i + 1 < len(parts):
                            results['car_number'] = parts[i+1]
                            break
        
        # 2단계: 중량 데이터 추출
        temp_weight = 0 # 라벨이 모호한 '중량' 키워드 발생 시 임시 보관

        for line in lines:
            line_lower = line.lower()
            val = 0

            # [우선순위 1] 'kg' 단위가 붙은 숫자 뭉치를 우선적으로 신뢰하여 추출
            kg_match = re.search(r'(\d+(?:,\d{3})*)\s*kg', line_lower)
            if kg_match:
                val = int(kg_match.group(1).replace(',', ''))
            else:
                # [우선순위 2] kg가 없더라도 줄 마지막에 위치한 숫자 덩어리를 후보로 채택
                raw_nums = re.findall(r'(\d[\d,]+)', line_lower)
                if not raw_nums: continue
                try:
                    val = int(raw_nums[-1].replace(',', ''))
                except (ValueError, IndexError):
                    continue
            
            if val == 0: continue

            # "총 중 량" 등 띄어쓰기가 포함된 키워드 대응
            clean_line = line_lower.replace(" ", "")

            # 추출된 숫자를 문맥(키워드)에 따라 해당 필드에 할당
            if any(k in clean_line for k in ["실중량", "순중량"]):
                if results['weights']['net'] == 0: results['weights']['net'] = val
            elif any(k in clean_line for k in ["공차중량", "차중량"]):
                if results['weights']['empty'] == 0: results['weights']['empty'] = val
            elif any(k in clean_line for k in ["총중량"]):
                if results['weights']['total'] == 0: results['weights']['total'] = val
            elif '품명' in clean_line:
                # 표 형식이 깨져 품명 줄에 총중량이 걸리는 예외 상황 대응
                if results['weights']['total'] == 0: results['weights']['total'] = val
            elif '중량' in clean_line:
                # 라벨이 불명확한 '중량'은 보관 후 검증 로직에서 처리
                if temp_weight == 0: temp_weight = val

        # 라벨이 누락된 값을 산술적으로 비어있는 필드에 보충
        if results['weights']['net'] > 0 and temp_weight > 0 and results['weights']['empty'] == 0:
            results['weights']['empty'] = temp_weight
        
        # 3단계: 데이터 산술 검증 및 부족한 값 추론 (Verification & Inference)
        # 비즈니스 로직: 총중량(Total) = 실중량(Net) + 공차중량(Empty)
        w = results['weights']
        
        # [검증 1] Total과 Empty가 확보된 경우 -> Net 강제 계산
        if w['total'] > 0 and w['empty'] > 0:
            calculated_net = w['total'] - w['empty']
            if calculated_net >= 0: w['net'] = calculated_net
            
        # [검증 2] Net과 Empty만 확보된 경우 -> Total 추론
        elif w['empty'] > 0 and w['net'] > 0 and w['total'] == 0:
            w['total'] = w['empty'] + w['net']
            
        # [검증 3] Total과 Net만 확보된 경우 -> Empty 추론
        elif w['total'] > 0 and w['net'] > 0 and w['empty'] == 0:
            calculated_empty = w['total'] - w['net']
            if calculated_empty >= 0: w['empty'] = calculated_empty
            
        return results