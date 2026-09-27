import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import crud
import schemas
from database import SessionLocal
# ※ 実際の models.py の定義に合わせてインポートを調整してください
from models import EDNAPrediction, Hotpoint

# ==================== 設定情報 ====================
# Hotpointとして抽出する閾値（例: intensity_score や prediction_value が 0.8 以上）
HOTPOINT_THRESHOLD = 0.8

# 何日先までの予測データを処理対象にするか
TARGET_DAYS_AHEAD = 3

# ==================== 抽出・保存処理 ====================
def generate_and_save_hotpoints(start_date=None):
    db = SessionLocal()
    try:
        print("======================================================")
        print(" 🔥 予測データからの Hotpoint 自動抽出・保存処理")
        print("======================================================\n")

        # 手動実行時などで開始日が指定されていればそれを使用、なければ現在時刻
        if start_date:
            now = start_date
        else:
            now = datetime.now()
            
        target_end_time = now + timedelta(days=TARGET_DAYS_AHEAD)
        
        print(f"対象期間: {now.strftime('%Y-%m-%d %H:%M:%S')} 〜 {target_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"抽出閾値: {HOTPOINT_THRESHOLD} 以上")

        # 2. eDNA_Prediction テーブルから、条件に合う高濃度の予測データを取得
        # ※実際のモデル定義のプロパティ名（predicted_timestamp 等）に合わせて変更してください
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
                # Hotpointモデルのインスタンス化
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

# ==================== メイン実行制御 ====================
if __name__ == "__main__":
    # コマンドライン引数で日付(YYYY-MM-DD)が渡されたら「手動実行モード」として動く
    if len(sys.argv) > 1:
        try:
            manual_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
            print(f"--- 手動実行モード: {sys.argv[1]} を基準日にして処理します ---")
            generate_and_save_hotpoints(start_date=manual_date)
        except ValueError:
            print("❌ 日付のフォーマットが間違っています。例: python generate_hotpoints.py 2026-05-12")
    else:
        print("--- 定期実行モード (現在時刻を基準に自動処理) ---")
        generate_and_save_hotpoints()
