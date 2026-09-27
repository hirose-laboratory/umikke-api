import sys
import traceback
from datetime import datetime

# 作成済みの各処理モジュールをインポート
import test_csv
import infer_and_export
import generate_hotpoints

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

    try:
        # ----------------------------------------------------
        # [1] CSVデータのDB登録処理 (test_csv.py)
        # ----------------------------------------------------
        print("\n>>> [1/3] 海況CSVデータのDB登録を開始します...")
        test_csv.main() 

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

if __name__ == "__main__":
    main()
  
