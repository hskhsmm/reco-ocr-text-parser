import re

def clean_text(text: str) -> str:
    if not text:
        return ""

    # 1. 별표(*) 및 불필요한 특수기호 제거
    text = re.sub(r'[\*]+', '', text)

    # 2. OCR 오타 및 중복 텍스트 교정
    replacements = {
        "계 그 표": "계량증명표",      # sample_02
        "입 고입고": "입고",           # sample_04 중복
        "공육을 unle": "",             # sample_03 의미없는 노이즈
        "품종명랑": "품명:",           # sample_01 오타
        "명:": "명 :",                 # 일관성 있는 라벨링
        "중 량:": "중량 :",
        "날 짜:": "날짜 :"
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)

    # 3. 불필요한 공백 및 줄바꿈 정리
    # 여러 개의 공백을 하나로
    text = re.sub(r' +', ' ', text)
    # 양끝 공백 제거
    text = text.strip()

    return text