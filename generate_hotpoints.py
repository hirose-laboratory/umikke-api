from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import crud
import schemas
from database import SessionLocal
from models import EDNAPrediction, Hotpoint

# 抽出条件の設定
HOTPOINT_THRESHOLD = 0.8
TARGET_DAYS_AHEAD = 60

def generate_and_save_hotpoints(base_time: datetime):
    """
    指定された基準日時から一定期間内の予測データのうち、
    閾値以上のものをHotpointとして抽出・保存する。
    """
    db = SessionLocal()
    try:
        target_end_time = base_time + timedelta(days=TARGET_DAYS_AHEAD)
        
        # 指定期間および閾値以上の予測データを取得
        high_density_predictions = db.query(EDNAPrediction).filter(
            EDNAPrediction.target_timestamp >= base_time,
            EDNAPrediction.target_timestamp <= target_end_time,
            EDNAPrediction.heatmap_value >= HOTPOINT_THRESHOLD
        ).all()

        if not high_density_predictions:
            return

        hotpoints_to_insert = []
        for pred in high_density_predictions:
            # 同一条件のデータが既に存在するか確認
            existing_hotpoint = db.query(Hotpoint).filter(
                Hotpoint.fish_id == pred.fish_id,
                Hotpoint.latitude == pred.latitude,
                Hotpoint.longitude == pred.longitude,
                Hotpoint.detected_timestamp == pred.target_timestamp
            ).first()

            if not existing_hotpoint:
                new_hotpoint = Hotpoint(
                    fish_id=pred.fish_id,
                    latitude=pred.latitude,
                    longitude=pred.longitude,
                    detected_timestamp=pred.target_timestamp,
                    intensity_score=pred.heatmap_value
                )
                hotpoints_to_insert.append(new_hotpoint)

        # 新規データが存在する場合のみ一括登録を実行
        if hotpoints_to_insert:
            db.add_all(hotpoints_to_insert)
            db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error in generate_and_save_hotpoints: {e}")
    finally:
        db.close()
        
