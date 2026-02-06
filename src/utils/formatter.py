import re


def merge_split_number_kg(text: str) -> str:
    """'kg' 앞의 숫자가 공백으로 분리된 경우 병합한다.

    예: '13 460 kg' -> '13460kg'
    """
    if not text:
        return ""
    return re.sub(r"(\d+)\s+(\d+)\s*kg", r"\1\2kg", text, flags=re.IGNORECASE)


def is_noise_line(line: str) -> bool:
    """발급사(issuer) 후보 판단 시 제외할 노이즈 라인 판별.

    날짜/시간/좌표 유사 소수/순수 숫자/무게(kg) 패턴과 일치하면 제외한다.
    기존 로직과 동일한 휴리스틱을 유지한다.
    """
    if not line:
        return True

    ls = line.strip()
    # 줄 시작의 날짜 패턴(예: 2025-12-01, 2025.12.01)
    if re.search(r"^\d{4}[-\/.]\d{2}[-\/.]\d{2}", ls):
        return True
    # 무게 단위 'kg'가 포함된 경우
    if re.search(r"[\d,]+\s*kg", ls, re.IGNORECASE):
        return True
    # 시간 패턴(예: 02:07)
    if re.search(r"\b\d{2}:\d{2}\b", ls):
        return True
    # 좌표 유사 소수 패턴(예: 37.12345)
    if re.search(r"^\d{2,3}\.\d{5,}", ls):
        return True
    # 순수 숫자만 있는 경우
    if re.fullmatch(r"\d+", ls):
        return True
    return False
