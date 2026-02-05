import json
from pathlib import Path
from src.parser.cleaner import clean_text

def run_cleaning_pipeline():
    data_dir = Path("data")
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True) # 폴더 없으면 생성

    # 모든 JSON 파일 순회
    for json_file in data_dir.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            raw_text = data.get('text', '')
            
            # 정제 실행
            cleaned = clean_text(raw_text)
            
            print(f" {json_file.name} 정제 완료")
            print(f"--- 정제된 텍스트 일부 ---\n{cleaned[:100]}...\n")

            # (선택) 정제된 텍스트를 나중에 쓰기 위해 메모리에 저장하거나 출력 가능

if __name__ == "__main__":
    run_cleaning_pipeline()