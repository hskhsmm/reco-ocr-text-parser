import json
import logging
from pathlib import Path
import argparse
import os
from src.parser.cleaner import clean_text
from src.parser.extractor import OcrExtractor

logger = logging.getLogger(__name__)


def setup_logging():
    """콘솔 + 파일 동시 출력 로깅 설정"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 파일 핸들러
    file_handler = logging.FileHandler("logs/pipeline.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def run_cleaning_pipeline(use_nlp: bool = False):
    data_dir = Path("data")
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    # 선택적 NLP 보조 모드 (플래그 또는 환경변수 USE_NLP)
    use_nlp = use_nlp or str(os.getenv("USE_NLP", "")).lower() in {"1", "true", "yes", "on"}
    if use_nlp:
        try:
            from src.nlp.engine import build_nlp  # lazy import
            from src.parser.extractor import OcrExtractor as BaseExtractor
            from src.parser.extractor_nlp_wrapper import OcrExtractorWithNlp
            nlp = build_nlp()
            extractor = OcrExtractorWithNlp(base=BaseExtractor(), nlp=nlp)
            logger.info("NLP 보조 모드 활성화: EntityRuler 적용")
        except Exception as e:
            logger.warning("NLP 보조 모드 초기화 실패: %s (기본 모드로 진행)", e)
            extractor = OcrExtractor()
    else:
        extractor = OcrExtractor()

    for json_file in data_dir.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            raw_text = data.get('text', '')

            cleaned = clean_text(raw_text)
            extracted_data = extractor.extract(cleaned)

            # 필드 누락 경고
            if extracted_data['car_number'] == "N/A":
                logger.warning("[%s] 차량번호 추출 실패", json_file.name)
            if extracted_data['date'] == "N/A":
                logger.warning("[%s] 날짜 추출 실패", json_file.name)

            # 무게 검증
            w = extracted_data['weights']
            if w['total'] > 0 and w['empty'] > 0 and w['net'] > 0:
                if w['total'] != w['empty'] + w['net']:
                    logger.warning(
                        "[%s] 무게 산술 불일치: total(%d) != empty(%d) + net(%d)",
                        json_file.name, w['total'], w['empty'], w['net']
                    )

            # 결과물 JSON 파일로 저장
            output_path = output_dir / f"{json_file.stem}_result.json"
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(extracted_data, out_f, ensure_ascii=False, indent=4)

            logger.info("[%s] 처리 완료 → %s", json_file.name, extracted_data)

    logger.info("전체 파이프라인 완료")


if __name__ == "__main__":
    setup_logging()
    run_cleaning_pipeline()
