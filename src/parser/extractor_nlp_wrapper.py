import re
from typing import Any


class OcrExtractorWithNlp:
    """기존 OcrExtractor를 감싸 spaCy EntityRuler로 N/A 필드만 보조 채우는 래퍼.

    - 기본 결과를 변경하지 않기 위해, base.extract() 실행 후 비어있는 필드만 보완한다.
    - 숫자/날짜/차량번호 등은 건드리지 않는다.
    """

    def __init__(self, base: Any, nlp: Any):
        self.base = base
        self.nlp = nlp

    def extract(self, text: str) -> dict:
        results = self.base.extract(text)

        lines = text.split("\n")

        # issuer_name 보조: ORG 엔티티가 있는 의미 라인 채택
        if results.get("issuer_name") == "N/A":
            for line in lines:
                ls = line.strip()
                if not ls:
                    continue
                doc = self.nlp(ls)
                if any(getattr(ent, 'label_', None) == "ORG" for ent in getattr(doc, 'ents', [])):
                    results['issuer_name'] = self._norm_korean(ls)
                    break

        # issuer_address 보조: LOC 엔티티가 있는 줄
        if results.get("issuer_address") == "N/A":
            for line in lines:
                ls = line.strip()
                if not ls:
                    continue
                doc = self.nlp(ls)
                if any(getattr(ent, 'label_', None) == "LOC" for ent in getattr(doc, 'ents', [])):
                    results['issuer_address'] = ls
                    break

        # client_name 보조: '귀하' 패턴 포함 줄에서 ORG 엔티티가 있을 때
        if results.get("client_name") == "N/A":
            for line in lines:
                ls = line.strip()
                if not ls or '귀' not in ls:
                    continue
                doc = self.nlp(ls)
                if any(getattr(ent, 'label_', None) == "ORG" for ent in getattr(doc, 'ents', [])):
                    name = re.sub(r"\s*귀\s*하\s*$", "", ls).strip()
                    results['client_name'] = self._norm_korean(name)
                    break

        return results

    @staticmethod
    def _norm_korean(text: str) -> str:
        # 한글 사이 불필요 공백 제거 + '(주)' 주변 공백 정리
        text = re.sub(r'(?<=[\uAC00-\uD7A3])\s+(?=[\uAC00-\uD7A3])', '', text)
        text = re.sub(r'\(\s*주\s*\)', '(주)', text)
        return text

