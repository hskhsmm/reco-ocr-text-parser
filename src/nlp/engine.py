import json
from pathlib import Path
from typing import Optional, Any


def _load_external_patterns(dir_path: Path) -> list:
    patterns = []
    if not dir_path.exists() or not dir_path.is_dir():
        return patterns
    for p in dir_path.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                patterns.extend(data)
        except Exception:
            # 외부 패턴 로드는 베스트에포트
            continue
    return patterns


def build_nlp(extra_patterns_dir: Optional[str] = "data/patterns") -> Any:
    """경량 spaCy 파이프라인을 구성한다.

    - blank("xx") + EntityRuler
    - 기본 ORG/LOC 패턴 내장
    - data/patterns/*.json 이 있으면 병합 로드
    """
    try:
        import spacy  # type: ignore
        from spacy.pipeline import EntityRuler  # type: ignore
    except Exception as e:
        raise ImportError(
            "spaCy가 설치되어 있지 않습니다. NLP 보조 모드를 사용하려면 'pip install -r requirements.txt' 또는 'pip install spacy==3.7.2'를 실행하세요."
        ) from e

    nlp = spacy.blank("xx")
    ruler = nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})

    # 기본 패턴(모델 학습 없이 동작)
    base_patterns = [
        # ORG: (주), 주식회사, 유한회사 등
        {"label": "ORG", "pattern": "(주)"},
        {"label": "ORG", "pattern": [{"LOWER": {"REGEX": "주식회사"}}]},
        {"label": "ORG", "pattern": [{"LOWER": {"REGEX": "유한회사"}}]},
        # LOC: 광역 지자체 접두(한 줄 내 등장 시 LOC로 간주)
        {"label": "LOC", "pattern": [{"TEXT": {"REGEX": "^(서울|경기|부산|인천|광주|대전|대구|울산|세종|강원|충북|충남|전북|전남|경북|경남)"}}]},
    ]

    ruler.add_patterns(base_patterns)

    # 외부 패턴 병합
    if extra_patterns_dir:
        patterns_dir = Path(extra_patterns_dir)
        ext = _load_external_patterns(patterns_dir)
        if ext:
            ruler.add_patterns(ext)

    return nlp
