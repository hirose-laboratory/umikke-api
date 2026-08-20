import csv
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
    filepath = "test.csv"

    records = load_ocean_data_from_csv(filepath)
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
