import json
from pathlib import Path
from src.parser.cleaner import clean_text
from src.parser.extractor import OcrExtractor

def run_cleaning_pipeline():
    data_dir = Path("data")
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True) 

    extractor = OcrExtractor()

    for json_file in data_dir.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            raw_text = data.get('text', '')
            
            # 텍스트 정제 및 데이터 추출
            cleaned = clean_text(raw_text)
            extracted_data = extractor.extract(cleaned)
            
            # 결과물 JSON 파일로 저장
            output_path = output_dir / f"{json_file.stem}_result.json"
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(extracted_data, out_f, ensure_ascii=False, indent=4)
            
            print(f" {json_file.name} 처리 및 저장 완료")
            print(f" 결과: {extracted_data}")
            print("-" * 50)

if __name__ == "__main__":
    run_cleaning_pipeline()