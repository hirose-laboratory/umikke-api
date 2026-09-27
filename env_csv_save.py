import argparse
import csv
import os
from typing import List, Optional

from sqlalchemy.orm import Session

import crud
import schemas
from database import SessionLocal

# ================================
# パス設定（本スクリプトの配置場所を基準にした絶対パス）
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_DIR = os.path.join(BASE_DIR, "CSV", "ocean")


def parse_float_or_default(value: Optional[str], default: float = 0.0) -> float:
    """
    文字列を float に変換します。
    空文字・None・変換失敗時はフロントエンド描画用のデフォルト値(0.0)を返します。
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
    CSVファイルを読み込み、schemas.OceanDataCreate のリストとして返します。
    ※フロントでの表示停止を防ぐため、欠損している項目は 0.0 に自動補正します。
    """
    records = []

    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=1):
            try:
                # 水温(sst)の判定
                raw_sst = row.get("sst")
                sst_val = (
                    float(raw_sst.strip())
                    if raw_sst and raw_sst.strip() != ""
                    else None
                )

                # 行データの構築とデフォルト値(0.0)適用
                cleaned_row = {
                    "latitude": float(row["latitude"].strip()),
                    "longitude": float(row["longitude"].strip()),
                    "record_timestamp": row["record_timestamp"].strip(),
                    "sst": sst_val,
                    # cha, current_speed, current_direction が空の場合は 0.0 をセット
                    "cha": parse_float_or_default(row.get("cha"), 0.0),
                    "current_speed": parse_float_or_default(row.get("current_speed"), 0.0),
                    "current_direction": parse_float_or_default(row.get("current_direction"), 0.0),
                }

                records.append(schemas.OceanDataCreate(**cleaned_row))
            except Exception as e:
                print(f"⚠️ [警告] {filepath} の {i}行目のデータを読み込めませんでした: {e}")

    return records


def import_ocean_csv_to_db(filepath: str, db: Session) -> int:
    """
    【外部呼び出し用】単一の海況データ CSV ファイルを DB に登録します。

    :param filepath: 対象CSVファイルのパス
    :param db: SQLAlchemy Session インスタンス
    :return: 登録されたレコード件数
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ファイルが存在しません: {filepath}")

    records = load_ocean_data_from_csv(filepath)
    if not records:
        print(f"⏩ {filepath} に有効な登録データが存在しませんでした。")
        return 0

    count = crud.create_ocean_data_bulk(db, records)
    print(f"✅ DB登録完了: {os.path.basename(filepath)} ({count} 件)")
    return count


def import_all_ocean_csvs_from_dir(csv_dir: str, db: Session) -> int:
    """
    【外部呼び出し / 手動実行用】指定ディレクトリ内の全 CSV ファイルを古い順にソートして
    DB に一括保存します。

    :param csv_dir: CSVファイルが配置されているフォルダパス
    :param db: SQLAlchemy Session インスタンス
    :return: 合計登録件数
    """
    if not os.path.exists(csv_dir):
        raise FileNotFoundError(f"指定されたディレクトリが存在しません: {csv_dir}")

    csv_files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    if not csv_files:
        print(f"ℹ️ {csv_dir} 内に処理対象のCSVファイルが見つかりません。")
        return 0

    total_inserted = 0
    # ファイル名（日付順など）でソートして順次実行
    for filename in sorted(csv_files):
        filepath = os.path.join(csv_dir, filename)
        try:
            count = import_ocean_csv_to_db(filepath, db)
            total_inserted += count
        except Exception as e:
            db.rollback()
            print(f"❌ DB登録失敗 ({filename}): {e}")

    return total_inserted


# ================================
# 手動実行用エントリーポイント (python import_ocean.py)
# ================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="海況データ (OceanData) の CSV インポート処理")
    parser.add_argument("--csv_path", type=str, default=None, help="単一のCSVファイルを登録する場合に指定")
    parser.add_argument("--dir_path", type=str, default=DEFAULT_CSV_DIR, help="フォルダ内の全CSVを一括登録する場合に指定 (デフォルト: CSV/ocean)")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.csv_path:
            print(f"🚀 [手動実行] 単一CSVのDB保存を開始: {args.csv_path}")
            total = import_ocean_csv_to_db(args.csv_path, db)
        else:
            # フォルダが存在しない場合（旧構成で CSV フォルダ直下にある場合への補正処理）
            target_dir = args.dir_path
            if not os.path.exists(target_dir):
                alt_dir = os.path.join(BASE_DIR, "CSV")
                if os.path.exists(alt_dir):
                    target_dir = alt_dir

            print(f"🚀 [手動実行] ディレクトリ内の全海況CSV一括登録を開始: {target_dir}")
            total = import_all_ocean_csvs_from_dir(target_dir, db)

        print(f"🎉 処理完了: 合計 {total} 件の海況データを DB に登録しました。")
    except Exception as e:
        db.rollback()
        print(f"❌ 処理中にエラーが発生しました: {e}")
    finally:
        db.close()
