import sys
import os
import traceback
from datetime import datetime
from database import SessionLocal

import env_csv_save
import infer_and_export
import edna_save
import generate_hotpoints

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OCEAN_CSV_DIR = os.path.join(BASE_DIR, "CSV")
EDNA_CSV_DIR = os.path.join(BASE_DIR, "CSV", "edna")

def main():
    if len(sys.argv) > 1:
        try:
            base_time = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        except ValueError:
            print("Error: 日付のフォーマットが間違っています。例: 2026-09-28")
            return
    else:
        base_time = datetime.now()

    db = SessionLocal()
    try:
        env_csv_save.import_all_ocean_csvs_from_dir(OCEAN_CSV_DIR, db)
        infer_and_export.run_inference_and_export(base_time=base_time)
        edna_save.import_all_edna_csvs_from_dir(EDNA_CSV_DIR, db)
        generate_hotpoints.generate_and_save_hotpoints(base_time=base_time)
        
    except Exception:
        db.rollback()
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
