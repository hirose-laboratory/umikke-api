import os
import csv
import argparse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import EDNAPrediction

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EDNA_CSV_DIR = os.path.join(BASE_DIR, "CSV", "edna")

def import_all_edna_csvs_from_dir(csv_dir: str, db: Session) -> int:
    if not os.path.exists(csv_dir):
        return 0

    csv_files = [f for f in os.listdir(csv_dir) if f.endswith(".csv")]
    total_inserted = 0

    for filename in sorted(csv_files):
        filepath = os.path.join(csv_dir, filename)
        records = []
        
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    records.append(EDNAPrediction(
                        fish_id=int(row["fish_id"]),
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        target_timestamp=row["target_timestamp"],
                        heatmap_value=float(row["heatmap_value"])
                    ))
                except Exception:
                    continue
        
        if records:
            try:
                db.add_all(records)
                db.commit()
                total_inserted += len(records)
            except Exception:
                db.rollback()
    
    return total_inserted

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir_path", type=str, default=DEFAULT_EDNA_CSV_DIR)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        import_all_edna_csvs_from_dir(args.dir_path, db)
    finally:
        db.close()
