import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Union
from sqlalchemy.orm import Session

import schemas
import models

# 保存先ディレクトリの自動生成
OUTPUT_DIR = os.path.join("CSV", "edna")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 対象エリアの空間定義（例：三重県沿岸部）
LAT_MIN, LAT_MAX = 34.22306, 34.37134
LON_MIN, LON_MAX = 136.64863, 136.95686


def export_edna_prediction_matrix_to_csv(
    heatmap_matrix: np.ndarray,
    fish_id: int,
    target_timestamp: datetime,
    output_filename: str = None,
    sea_mask: np.ndarray = None
) -> str:
    """
    【本番運用用】推論モデルが出力した2次元グリッド行列(H, W)を
    座標補間・整形し、eDNA予測CSVファイルとして一括出力します。

    :param heatmap_matrix: モデルの出力行列（2次元 numpy 配列）
    :param fish_id: 魚種ID (models.FishData.id)
    :param target_timestamp: 予測対象の日時 (datetime)
    :param output_filename: 指定の出力ファイル名（未指定時は日付から自動生成）
    :param sea_mask: 陸地マスク (True: 海域, False: 陸地)。指定時は陸地を除外
    :return: 保存されたCSVファイルのパス
    """
    h, w = heatmap_matrix.shape
    lats = np.linspace(LAT_MAX, LAT_MIN, h)
    lons = np.linspace(LON_MIN, LON_MAX, w)

    ts_str = target_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    records = []
    for r in range(h):
        for c in range(w):
            # 陸地マスクがある場合は海域のみ抽出
            if sea_mask is not None and not sea_mask[r, c]:
                continue

            val = float(heatmap_matrix[r, c])
            records.append({
                "fish_id": fish_id,
                "latitude": round(float(lats[r]), 6),
                "longitude": round(float(lons[c]), 6),
                "target_timestamp": ts_str,
                "heatmap_value": round(val, 4)
            })

    # Pydantic スキーマによるデータ構造の検証
    validated_data = [schemas.EDNAPredictionBase(**rec).model_dump() for rec in records]
    df = pd.DataFrame(validated_data)

    # 出力ファイル名の指定（デフォルト: edna_pred_{fish_id}_{YYYYMMDD}.csv）
    if not output_filename:
        dt_str = target_timestamp.strftime("%Y%m%d")
        output_filename = f"edna_pred_{fish_id}_{dt_str}.csv"

    file_path = os.path.join(OUTPUT_DIR, output_filename)
    df.to_csv(file_path, index=False, encoding="utf-8")
    
    return file_path


def export_edna_prediction_db_to_csv(
    db: Session,
    fish_id: int,
    start_time: datetime = None,
    end_time: datetime = None
) -> str:
    """
    【本番運用用】データベース(eDNA_Prediction)内のレコードを検索し、
    CSVファイルとして保存（エクスポート）します。
    """
    query = db.query(models.EDNAPrediction).filter(models.EDNAPrediction.fish_id == fish_id)

    if start_time:
        query = query.filter(models.EDNAPrediction.target_timestamp >= start_time)
    if end_time:
        query = query.filter(models.EDNAPrediction.target_timestamp <= end_time)

    results = query.all()

    if not results:
        raise ValueError(f"指定された条件に該当するeDNA予測データが存在しません (fish_id: {fish_id})")

    # DBオブジェクトをスキーマ経由で辞書化
    records = [
        schemas.EDNAPredictionResponse.model_validate(row).model_dump()
        for row in results
    ]

    df = pd.DataFrame(records)
    
    # 日時表記の整形
    if "target_timestamp" in df.columns:
        df["target_timestamp"] = pd.to_datetime(df["target_timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(OUTPUT_DIR, f"edna_db_export_fish{fish_id}_{timestamp_str}.csv")
    df.to_csv(file_path, index=False, encoding="utf-8")

    return file_path
