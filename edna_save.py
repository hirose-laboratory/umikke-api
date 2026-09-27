import argparse
import os
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

import models
import schemas
from database import SessionLocal

# ================================
# パス設定（本スクリプトの配置場所を基準にした絶対パス）
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_DIR = os.path.join(BASE_DIR, "CSV", "edna")


def import_edna_csv_to_db(csv_file_path: str, db: Session) -> int:
    """
    【外部呼び出し用】1つの eDNA CSV ファイルを読み込み、
    データベース (eDNA_Prediction テーブル) に保存します。

    :param csv_file_path: 対象CSVファイルのパス
    :param db: SQLAlchemy Session インスタンス
    :return: 登録されたレコード件数
    """
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSVファイルが存在しません: {csv_file_path}")

    # CSVファイルのロード
    df = pd.read_csv(csv_file_path)

    # 必須カラムチェック
    required_cols = {"fish_id", "latitude", "longitude", "target_timestamp", "heatmap_value"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"CSVのカラムが不十分です。不足: {missing} (ファイル: {csv_file_path})")

    if df.empty:
        return 0

    records = df.to_dict(orient="records")
    
    # 型変換および Pydantic バリデーション
    mappings = []
    for row in records:
        # target_timestamp の datetime 変換
        target_ts = pd.to_datetime(row["target_timestamp"]).to_pydatetime()
        
        # schemas.EDNAPredictionBase による入力検証
        valid_data = schemas.EDNAPredictionBase(
            fish_id=int(row["fish_id"]),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            target_timestamp=target_ts,
            heatmap_value=float(row["heatmap_value"]) if pd.notna(row["heatmap_value"]) else None
        )
        mappings.append(valid_data.model_dump())

    # バルクインサート処理（高速一括登録）
    db.bulk_insert_mappings(models.EDNAPrediction, mappings)
    db.commit()

    return len(mappings)


def import_all_edna_csvs_from_dir(csv_dir: str, db: Session) -> int:
    """
    【外部呼び出し / 手動実行用】指定ディレクトリ内のすべての CSV ファイルを順次読み込み、
    DB (eDNA_Prediction テーブル) に保存します。

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
    for filename in sorted(csv_files):
        file_path = os.path.join(csv_dir, filename)
        try:
            count = import_edna_csv_to_db(file_path, db)
            total_inserted += count
            print(f"✅ DB登録完了: {filename} ({count} 件)")
        except Exception as e:
            db.rollback()
            print(f"❌ DB登録失敗 ({filename}): {e}")

    return total_inserted


# ================================
# 手動実行時のメイン処理 (python import_edna.py)
# ================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSV形式の eDNA 予測データを DB (eDNA_Prediction) に保存します。")
    parser.add_argument("--csv_path", type=str, default=None, help="単一のCSVファイルを保存する場合に指定")
    parser.add_argument("--dir_path", type=str, default=DEFAULT_CSV_DIR, help="フォルダ内の全CSVを一括保存する場合に指定 (デフォルト: CSV/edna)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.csv_path:
            print(f"🚀 [手動実行] 単一CSVのDB保存を開始: {args.csv_path}")
            count = import_edna_csv_to_db(args.csv_path, db)
            print(f"🎉 完了: {count} 件のレコードを DB に登録しました。")
        else:
            print(f"🚀 [手動実行] ディレクトリ内の全CSV一括登録を開始: {args.dir_path}")
            total = import_all_edna_csvs_from_dir(args.dir_path, db)
            print(f"🎉 完了: 合計 {total} 件のレコードを DB に登録しました。")
    except Exception as e:
        db.rollback()
        print(f"❌ 処理中にエラーが発生しました: {e}")
    finally:
        db.close()
