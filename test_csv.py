import csv
import os
from datetime import datetime

from database import SessionLocal
import crud
import schemas


def load_ocean_data_from_csv(filepath: str) -> list[schemas.OceanDataCreate]:
    records = []

    with open(filepath, mode="r", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=1):
            try:
                records.append(schemas.OceanDataCreate(**row))
            except Exception as e:
                # 不正な行があってもそこだけスキップして続行する
                print(f"[警告] {i}件目のデータを読み込めませんでした: {e}")

    return records


def main():
    csv_dir = "CSV"
    csv_files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    
    if not csv_files:
        print(f"{csv_dir} フォルダにCSVファイルがありません")
        return
        
    db = SessionLocal()
    total_count = 0
    try:
        for filename in csv_files:
            filepath = os.path.join(csv_dir, filename)
            records = load_ocean_data_from_csv(filepath)
            print(f"{filepath} から {len(records)} 件を読み込みました")
            
            if not records:
                print(f"{filepath} は登録対象がないためスキップします")
                continue
            count = crud.create_ocean_data_bulk(db, records)
            total_count += count
            print(f"{filepath} から OceanDataに{count}件登録しました")

    finally:
        db.close()
    print(f"合計 {total_count} 件を登録しました")

if __name__ == "__main__":
    main()
