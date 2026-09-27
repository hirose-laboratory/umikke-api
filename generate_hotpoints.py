import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import crud
import schemas
from database import SessionLocal
from models import EDNAPrediction, Hotpoint  # models.py に定義されていると想定

# ==================== 設定情報 ====================
# Hotpointとして抽出する閾値（例: prediction_value が 0.8 以上のものを抽出）
HOTPOINT_THRESHOLD = 0.8

# 何日先までの予測データを処理対象にするか（例: 向こう3日分）
TARGET_DAYS_AHEAD = 3

# ==================== 抽出・保存処理 ====================
def generate_and_save_hotpoints():
    db = SessionLocal()
    try:
        print("======================================================")
        print(" 🔥 予測データからの Hotpoint 自動抽出・保存処理")
        print("======================================================\n")

        # 1. 処理対象の期間を設定（現在時刻〜指定日数後まで）
        now = datetime.now()
        target_end_time = now + timedelta(days=TARGET_DAYS_AHEAD)
        
        print(f"対象期間: {now.strftime('%Y-%m-%d %H:%M:%S')} 〜 {target_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"抽出閾値 (intensity_score): {HOTPOINT_THRESHOLD} 以上")

        # 2. eDNA_Prediction テーブルから、条件に合う高濃度の予測データを取得
        # ※実際のモデル定義（models.EDNAPrediction）のプロパティ名に合わせて変更してください
        high_density_predictions = db.query(EDNAPrediction).filter(
            EDNAPrediction.predicted_timestamp >= now,
            EDNAPrediction.predicted_timestamp <= target_end_time,
            EDNAPrediction.prediction_value >= HOTPOINT_THRESHOLD
        ).all()

        if not high_density_predictions:
            print("ℹ️ 条件を満たす Hotpoint候補は見つかりませんでした。")
            return

        print(f"🔍 {len(high_density_predictions)} 件の Hotpoint候補を抽出しました。保存処理を開始します...")

        # 3. 抽出したデータを Hotpoint テーブルの形式に変換して保存
        hotpoints_to_insert = []
        for pred in high_density_predictions:
            # 既に同じ座標・日時のHotpointが存在するかチェック（重複防止）
            existing_hotpoint = db.query(Hotpoint).filter(
                Hotpoint.fish_id == pred.fish_id,
                Hotpoint.latitude == pred.latitude,
                Hotpoint.longitude == pred.longitude,
                Hotpoint.detected_timestamp == pred.predicted_timestamp
            ).first()

            if not existing_hotpoint:
                # schemas や crud を使わず、直接 SQLAlchemy の Model をインスタンス化して一括保存する
                new_hotpoint = Hotpoint(
                    fish_id=pred.fish_id,
                    latitude=pred.latitude,
                    longitude=pred.longitude,
                    detected_timestamp=pred.predicted_timestamp,
                    intensity_score=pred.prediction_value
                )
                hotpoints_to_insert.append(new_hotpoint)

        # 4. データベースへ一括登録（バルクインサート）
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
        print("\n=== 処理完了 ===")

if __name__ == "__main__":
    generate_hotpoints()
