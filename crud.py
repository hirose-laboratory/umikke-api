from sqlalchemy.orm import Session
from datetime import datetime
import models

# ================================
# Users & Groups
# ================================
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_users_by_group(db: Session, group_id: int):
    return db.query(models.User).filter(models.User.group_id == group_id).all()

def get_groups(db: Session):
    return db.query(models.Group).all()

# ================================
# FishData & eDNA & Hotpoint
# ================================
def get_fish_data(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.FishData).offset(skip).limit(limit).all()

def get_fish_by_name(db: Session, name: str):
    return db.query(models.FishData).filter(models.FishData.fish_name.contains(name)).all()

def get_edna_actual_by_fish(db: Session, fish_id: int):
    return db.query(models.EDNAActual).filter(models.EDNAActual.fish_id == fish_id).all()

def get_hotpoints_above_score(db: Session, min_score: float, limit: int = 50):
    return db.query(models.Hotpoint).filter(models.Hotpoint.intensity_score >= min_score).order_by(models.Hotpoint.intensity_score.desc()).limit(limit).all()

def get_suggestions_by_fish(db: Session, fish_id: int):
    return db.query(models.Suggest).filter(models.Suggest.fish_id == fish_id).all()

# ================================
# OceanData (期間・範囲指定による抽出パターン)
# ================================
def get_ocean_data(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.OceanData).order_by(models.OceanData.record_timestamp.desc()).offset(skip).limit(limit).all()

def get_ocean_data_by_time_range(db: Session, start_time: datetime, end_time: datetime):
    return db.query(models.OceanData).filter(
        models.OceanData.record_timestamp >= start_time,
        models.OceanData.record_timestamp <= end_time
    ).all()