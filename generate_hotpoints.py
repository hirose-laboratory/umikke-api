from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import crud
import schemas
from database import SessionLocal
from models import EDNAPrediction, Hotpoint

# ==================== 設定情報 ====================
HOTPOINT_THRESHOLD = 0.8
TARGET_DAYS_AHEAD = 3

# ==================== 抽出・保存処理 ====================
def generate_and_save_hotpoints(base_time: datetime):
    """
    メインスクリプトから渡された base_time を基準に Hotpoint を抽出・保存する
    """
    db = SessionLocal()
    try:
        print("======================================================")
        print(" 🔥 予測データからの Hotpoint 自動抽出・保存処理")
        print("======================================================\n")

        target_end_time = base_time + timedelta(days=TARGET_DAYS_AHEAD)
        
        print(f"対象期間: {base_time.strftime('%Y-%m-%d %H:%M:%S')} 〜 {target_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"抽出閾値: {HOTPOINT_THRESHOLD} 以上")

        # EDNAPredictionの正しいカラム名（target_timestamp, heatmap_value）を使用
        high_density_predictions = db.query(EDNAPrediction).filter(
            EDNAPrediction.target_timestamp >= base_time,
            EDNAPrediction.target_timestamp <= target_end_time,
            EDNAPrediction.heatmap_value >= HOTPOINT_THRESHOLD
        ).all()

        if not high_density_predictions:
            print("ℹ️ 条件を満たす Hotpoint候補は見つかりませんでした。")
            return

        print(f"🔍 {len(high_density_predictions)} 件の Hotpoint候補を抽出しました。保存処理を開始します...")

        hotpoints_to_insert = []
        for pred in high_density_predictions:
            # 既存チェック
            existing_hotpoint = db.query(Hotpoint).filter(
                Hotpoint.fish_id == pred.fish_id,
                Hotpoint.latitude == pred.latitude,
                Hotpoint.longitude == pred.longitude,
                Hotpoint.detected_timestamp == pred.target_timestamp
            ).first()

            if not existing_hotpoint:
                # Hotpointモデルのインスタンス化
                new_hotpoint = Hotpoint(
                    fish_id=pred.fish_id,
                    latitude=pred.latitude,
                    longitude=pred.longitude,
                    detected_timestamp=pred.target_timestamp,
                    intensity_score=pred.heatmap_value
                )
                hotpoints_to_insert.append(new_hotpoint)

        # データベースへ一括登録
        if hotpoints_to_insert:
            db.add_all(hotpoints_to_insert)
            db.commit()
            print(f"✅ 計 {len(hotpoints_to_insert)} 件の新しい Hotpoint をデータベースに保存しました。")
        else:
            print("ℹ️ 新しく追加すべき Hotpoint はありませんでした（すべて登録済み）。")

    except Exception as e:
        db.rollback()
        print(f"❌ Hotpoint 抽出・保存処理中にエラーが発生しました: {e}")
    finally:
        db.close()
