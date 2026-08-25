import csv
import os
from datetime import datetime

from database import SessionLocal
import crud
import schemas

def load_ocean_data_from_csv(filepath: str) -> list[schemas.OceanDataCreate]:
    records = []

    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=1):
            # 【重要】CSVの空文字("")をNoneに変換し、Pydanticのfloat変換エラーを防ぐ
            cleaned_row = {k: (v if v != "" else None) for k, v in row.items()}
            
            try:
                # 変換済みの辞書を展開してスキーマに渡す
                records.append(schemas.OceanDataCreate(**cleaned_row))
            except Exception as e:
                # 不正な行があってもそこだけスキップして続行する
                print(f"⚠️ [警告] {filepath} の {i}件目のデータを読み込めませんでした: {e}")

    return records


def main():
    csv_dir = "CSV"
    
    # ディレクトリが存在しない場合の安全対策
    if not os.path.exists(csv_dir):
        print(f"❌ {csv_dir} フォルダが存在しません。")
        return

    csv_files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    
    if not csv_files:
        print(f"ℹ️ {csv_dir} フォルダにCSVファイルがありません。")
        return
        
    db = SessionLocal()
    total_count = 0
    
    try:
        # 【重要】ファイル名（日付）順にソートして、古いデータから順番に登録する
        for filename in sorted(csv_files):
            filepath = os.path.join(csv_dir, filename)
            records = load_ocean_data_from_csv(filepath)
            
            print(f"📄 {filepath} から {len(records)} 件を読み込みました")
            
            if not records:
                print(f"⏩ {filepath} は登録対象がないためスキップします")
                continue
                
            # DBへのバルクインサート（一括登録）
            count = crud.create_ocean_data_bulk(db, records)
            total_count += count
            print(f"✅ {filepath} から OceanDataに {count} 件登録しました")

            # ※必要に応じて、二重登録を防ぐために登録完了したCSVを削除・移動する場合は
            # 以下のコメントアウトを外してください。
            # os.remove(filepath)

    except Exception as e:
        print(f"❌ DB登録処理中に予期せぬエラーが発生しました: {e}")
    finally:
        db.close()
        
    print(f"🎉 合計 {total_count} 件をデータベースに登録しました")

if __name__ == "__main__":
    main()
