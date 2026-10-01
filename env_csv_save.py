import argparse
import csv
import os
from typing import List, Optional

from sqlalchemy.orm import Session

import crud
import schemas
from database import SessionLocal

# ベースディレクトリとデフォルトのCSVフォルダパスの設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_DIR = os.path.join(BASE_DIR, "CSV", "ocean")


def parse_float_or_default(value: Optional[str], default: float = 0.0) -> float:
    """
    文字列をfloat型に変換する。
    空文字やNone、変換エラーの場合はデフォルト値（0.0）を返す。
    """
    if value is None:
        return default
    
    if isinstance(value, str):
        val_str = value.strip()
        if val_str == "":
            return default
        try:
            return float(val_str)
        except ValueError:
            return default
            
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def load_ocean_data_from_csv(filepath: str) -> List[schemas.OceanDataCreate]:
    """
    CSVファイルを読み込み、OceanDataCreateスキーマのリストに変換する。
    欠損値はデフォルト値（0.0）に補正する。
    """
    records = []

    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=1):
            try:
                raw_sst = row.get("sst")
                sst_val = (
                    float(raw_sst.strip())
                    if raw_sst and raw_sst.strip() != ""
                    else None
                )

                cleaned_row = {
                    "latitude": float(row["latitude"].strip()),
                    "longitude": float(row["longitude"].strip()),
                    "record_timestamp": row["record_timestamp"].strip(),
                    "sst": sst_val,
                    "cha": parse_float_or_default(row.get("cha"), 0.0),
                    "current_speed": parse_float_or_default(row.get("current_speed"), 0.0),
                    "current_direction": parse_float_or_default(row.get("current_direction"), 0.0),
                }

                records.append(schemas.OceanDataCreate(**cleaned_row))
            except Exception:
                # 変換に失敗した不正な行データはスキップする
                pass

    return records


def import_ocean_csv_to_db(filepath: str, db: Session) -> int:
    """
    単一のCSVファイルをデータベースに登録する。
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ファイルが存在しません: {filepath}")

    records = load_ocean_data_from_csv(filepath)
    if not records:
        return 0

    count = crud.create_ocean_data_bulk(db, records)
    return count


def import_all_ocean_csvs_from_dir(csv_dir: str, db: Session) -> int:
    """
    指定ディレクトリ内のすべてのCSVファイルをソートして一括でデータベースに登録する。
    """
    if not os.path.exists(csv_dir):
        raise FileNotFoundError(f"指定されたディレクトリが存在しません: {csv_dir}")

    csv_files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    if not csv_files:
        return 0

    total_inserted = 0
    for filename in sorted(csv_files):
        filepath = os.path.join(csv_dir, filename)
        try:
            count = import_ocean_csv_to_db(filepath, db)
            total_inserted += count
        except Exception:
            db.rollback()

    return total_inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="海況データのCSVインポート処理")
    parser.add_argument("--csv_path", type=str, default=None, help="単一のCSVファイルを登録する場合に指定")
    parser.add_argument("--dir_path", type=str, default=DEFAULT_CSV_DIR, help="フォルダ内の全CSVを一括登録する場合に指定")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.csv_path:
            import_ocean_csv_to_db(args.csv_path, db)
        else:
            target_dir = args.dir_path
            
            # ディレクトリが存在しない場合の代替パス設定
            if not os.path.exists(target_dir):
                alt_dir = os.path.join(BASE_DIR, "CSV")
                if os.path.exists(alt_dir):
                    target_dir = alt_dir

            import_all_ocean_csvs_from_dir(target_dir, db)
            
    except Exception:
        db.rollback()
    finally:
        db.close()
