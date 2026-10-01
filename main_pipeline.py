import sys
import os
import traceback
from datetime import datetime
from database import SessionLocal

import env_csv_save
import infer_and_export
import generate_hotpoints

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(BASE_DIR, "CSV")

def main():
    # コマンドライン引数から処理の基準日時を決定する
    if len(sys.argv) > 1:
        try:
            # 手動実行: 引数で指定された日付を基準日とする
            base_time = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        except ValueError:
            print("Error: 日付のフォーマットが間違っています。例: python main_pipeline.py 2026-09-28")
            return
    else:
        # 定期実行: 実行時の現在時刻を基準日とする
        base_time = datetime.now()

    db = SessionLocal()
    try:
        # 1. CSVデータのDB登録処理
        try:
            total_inserted = env_csv_save.import_all_ocean_csvs_from_dir(CSV_DIR, db)
        except Exception as e:
            print(f"Error: 海況CSVデータのDB登録中にエラーが発生しました: {e}")
            db.rollback()
            raise 

        # 2. AI推論処理およびeDNAデータの出力・保存
        infer_and_export.run_inference_and_export(base_time=base_time)

        # 3. 予測結果に基づくHotpoint（漁場候補地）の抽出とDB登録
        generate_hotpoints.generate_and_save_hotpoints(base_time=base_time)

    except Exception as e:
        print(f"Error: パイプライン実行中にエラーが発生しました: {e}")
        traceback.print_exc()
    finally:
        # 処理の成否に関わらずデータベースセッションをクローズする
        db.close()

if __name__ == "__main__":
    main()
