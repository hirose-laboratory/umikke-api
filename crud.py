from sqlalchemy.orm import Session
from datetime import datetime
import schemas
import models
from passlib.context import CryptContext
from typing import Optional
from sqlalchemy import delete  # ← パターン1のために追加

# ================================
# Users & Groups
# ================================
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_users_by_group(db: Session, group_id: int):
    return db.query(models.User).filter(models.User.group_id == group_id).all()

def get_groups(db: Session):
    return db.query(models.Group).all()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    # パスワードをハッシュ化
    hashed_password = get_password_hash(user.password)
    
    # DBモデルのインスタンス作成
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        group_id=user.group_id,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

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

def get_edna_prediction_by_fish(db: Session, fish_id: int):
    return db.query(models.EDNAPrediction).filter(models.EDNAPrediction.fish_id == fish_id).all()


def create_edna_prediction(db: Session, prediction: schemas.EDNAPredictionBase):
    db_pred = models.EDNAPrediction(**prediction.model_dump())
    db.add(db_pred)
    db.commit()
    db.refresh(db_pred)
    return db_pred

# eDNA予測データの一括バルクインサート（予測モデル等の出力データ用）
def create_edna_prediction_bulk(db: Session, prediction_list: list[schemas.EDNAPredictionBase]):
    if not prediction_list:
        return 0
    mappings = [p.model_dump() for p in prediction_list]
    db.bulk_insert_mappings(models.EDNAPrediction, mappings)
    db.commit()
    return len(mappings)

def get_edna_actual_by_fish(db: Session, fish_id: int, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
    query = db.query(models.EDNAActual).filter(models.EDNAActual.fish_id == fish_id)
    if start_time:
        query = query.filter(models.EDNAActual.sample_timestamp >= start_time)
    if end_time:
        query = query.filter(models.EDNAActual.sample_timestamp <= end_time)
    return query.all()

# ホットポイント (期間指定対応)
def get_hotpoints_above_score(db: Session, min_score: float, limit: int = 50, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
    query = db.query(models.Hotpoint).filter(models.Hotpoint.intensity_score >= min_score)
    if start_time:
        query = query.filter(models.Hotpoint.detected_timestamp >= start_time)
    if end_time:
        query = query.filter(models.Hotpoint.detected_timestamp <= end_time)
    return query.order_by(models.Hotpoint.intensity_score.desc()).limit(limit).all()

# eDNA予測値 (期間指定対応)
def get_edna_prediction_by_fish(db: Session, fish_id: int, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
    query = db.query(models.EDNAPrediction).filter(models.EDNAPrediction.fish_id == fish_id)
    if start_time:
        query = query.filter(models.EDNAPrediction.target_timestamp >= start_time)
    if end_time:
        query = query.filter(models.EDNAPrediction.target_timestamp <= end_time)
    return query.all()

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

def create_ocean_data(db: Session, ocean: schemas.OceanDataCreate):
    db_ocean = models.OceanData(
        latitude=ocean.latitude,
        longitude=ocean.longitude,
        record_timestamp=ocean.record_timestamp,
        sst=ocean.sst,
        cha=ocean.cha,
        current_speed=ocean.current_speed,
        current_direction=ocean.current_direction,
    )
    db.add(db_ocean)
    db.commit()
    db.refresh(db_ocean)
    return db_ocean
    
def create_ocean_data_bulk(db: Session, ocean_list: list[schemas.OceanDataCreate]):
    if not ocean_list:
        return 0

    # 1. 挿入しようとしているデータの日付（record_timestamp）を抽出
    target_timestamps = list(set(o.record_timestamp for o in ocean_list))

    # 2. その日時のデータを一度DBから一括削除する（重複防止・上書きのため）
    if target_timestamps:
        db.execute(
            delete(models.OceanData).where(
                models.OceanData.record_timestamp.in_(target_timestamps)
            )
        )
        db.commit()

    # 3. 新しいデータを一括挿入
    mappings = [
        {
            "latitude": o.latitude,
            "longitude": o.longitude,
            "record_timestamp": o.record_timestamp,
            "sst": o.sst,
            "cha": o.cha,
            "current_speed": o.current_speed,
            "current_direction": o.current_direction,
        }
        for o in ocean_list
    ]

    db.bulk_insert_mappings(models.OceanData, mappings)
    db.commit()
    return len(mappings)
