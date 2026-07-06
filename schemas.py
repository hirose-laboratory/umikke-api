from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Groups ---
class GroupBase(BaseModel):
    group_name: str
    description: Optional[str] = None

class GroupResponse(GroupBase):
    id: int
    class Config:
        from_attributes = True

# --- Users ---
class UserBase(BaseModel):
    username: str
    email: str
    role: Optional[str] = 'viewer'

class UserResponse(UserBase):
    id: int
    group_id: Optional[int] = None
    created_at: datetime
    class Config:
        from_attributes = True

# --- FishData ---
class FishDataBase(BaseModel):
    fish_name: str
    scientific_name: Optional[str] = None

class FishDataResponse(FishDataBase):
    id: int
    class Config:
        from_attributes = True

# --- OceanData ---
class OceanDataResponse(BaseModel):
    id: int
    latitude: float
    longitude: float
    record_timestamp: datetime
    sst: Optional[float] = None
    cha: Optional[float] = None
    current_speed: Optional[float] = None
    current_direction: Optional[float] = None
    class Config:
        from_attributes = True

# --- eDNA ---
class EDNAActualResponse(BaseModel):
    id: int
    fish_id: int
    latitude: float
    longitude: float
    sample_timestamp: datetime
    concentration: Optional[float] = None
    class Config:
        from_attributes = True

# --- Hotpoint ---
class HotpointResponse(BaseModel):
    id: int
    fish_id: Optional[int] = None
    latitude: float
    longitude: float
    detected_timestamp: datetime
    intensity_score: Optional[float] = None
    class Config:
        from_attributes = True

# --- Suggest ---
class SuggestResponse(BaseModel):
    id: int
    hotpoint_id: Optional[int] = None
    fish_id: Optional[int] = None
    title: str
    message: str
    created_at: datetime
    class Config:
        from_attributes = True

# --- Users に追加 ---
class UserCreate(UserBase):
    password: str # 登録時には平文のパスワードを受け取る
    group_id: Optional[int] = None

# --- EDNAPrediction を新規追加 ---
class EDNAPredictionBase(BaseModel):
    fish_id: int
    latitude: float
    longitude: float
    target_timestamp: datetime
    heatmap_value: Optional[float] = None

class EDNAPredictionResponse(EDNAPredictionBase):
    id: int
    class Config:
        from_attributes = True
