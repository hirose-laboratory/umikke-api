import sys
import os
import traceback
from datetime import datetime
from database import SessionLocal

# 作成済みの各処理モジュールをインポート
import env_csv_save
import infer_and_export
import generate_hotpoints

# ================================
# パス設定（本スクリプトの配置場所を基準にした絶対パス）
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# もしサーバー上のCSVディレクトリ構成が異なる場合は、ここを "CSV" や "CSV/ocean" 等に合わせてください
CSV_DIR = os.path.join(BASE_DIR, "CSV")

def main():
    print("======================================================")
    print(" 🚀 海洋データ自動パイプライン (本番統合版) 実行開始")
    print("======================================================\n")

    # メインスクリプトで時間を一括取得し、各関数へ引き渡す
    if len(sys.argv) > 1:
        try:
            # 手動で日付が指定された場合 (例: python main_pipeline.py 2026-09-28)
            base_time = datetime.strptime(sys.argv[1], "%Y-%m-%d")
            print(f"--- ⚠️ 手動実行モード: {sys.argv[1]} を基準日に設定 ---")
        except ValueError:
            print("❌ 日付のフォーマットが間違っています。例: python main_pipeline.py 2026-09-28")
            return
    else:
        # cronからの定期実行時は「現在時刻」を取得
        base_time = datetime.now()
        print(f"--- 🕒 定期実行モード: {base_time.strftime('%Y-%m-%d %H:%M:%S')} ---")

    db = SessionLocal()
    try:
        # ----------------------------------------------------
        # [1] CSVデータのDB登録処理 (env_csv_save.py)
        # ----------------------------------------------------
        print("\n>>> [1/3] 海況CSVデータのDB登録を開始します...")
        try:
            # フォルダ内の全てのCSVを古い順にDBへ一括登録
            total_inserted = env_csv_save.import_all_ocean_csvs_from_dir(CSV_DIR, db)
            print(f"✅ 合計 {total_inserted} 件の海況データを DB に登録しました。")
        except Exception as e:
            print(f"❌ 海況CSVデータのDB登録中にエラーが発生しました: {e}")
            db.rollback()
            raise # ここで失敗した場合は後続のAI推論に影響するため処理を止める

        # ----------------------------------------------------
        # [2] AI推論処理 & eDNAデータ保存 (infer_and_export.py)
        # ----------------------------------------------------
        print("\n>>> [2/3] AI予測モデルの推論と結果出力を開始します...")
        infer_and_export.run_inference_and_export(base_time=base_time)

        # ----------------------------------------------------
        # [3] Hotpointの抽出と登録 (generate_hotpoints.py)
        # ----------------------------------------------------
        print("\n>>> [3/3] 予測結果から Hotpoint の自動抽出・保存を開始します...")
        generate_hotpoints.generate_and_save_hotpoints(base_time=base_time)
        
        print("\n🎉 全パイプライン処理が正常に完了しました！")

    except Exception as e:
        print(f"\n❌ パイプライン実行中に致命的なエラーが発生しました: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
