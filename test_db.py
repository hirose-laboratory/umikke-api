import json
from datetime import datetime

from database import SessionLocal
import crud
import schemas


def load_ocean_data_from_json(filepath: str) -> list[schemas.OceanDataCreate]:
    with open(filepath, encoding="utf-8") as f:
        raw_list = json.load(f)

    records = []
    for i, item in enumerate(raw_list):
        try:
            records.append(schemas.OceanDataCreate(**item))
        except Exception as e:
            # 不正な行があってもそこだけスキップして続行する
            print(f"[警告] {i}件目のデータを読み込めませんでした: {e}")

    return records


def main():
    filepath = "test.json"

    records = load_ocean_data_from_json(filepath)
    print(f"{filepath} から {len(records)} 件を読み込みました")

    if not records:
        print("登録対象がないため終了します")
        return

    db = SessionLocal()
    try:
        count = crud.create_ocean_data_bulk(db, records)
        print(f"OceanDataに{count}件登録しました")
    finally:
        db.close()


if __name__ == "__main__":
    main()
