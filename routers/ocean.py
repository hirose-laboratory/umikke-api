# routers/ocean.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import crud, schemas
from database import get_db

router = APIRouter(prefix="/ocean", tags=["Ocean Data"])

# 海洋データを一覧取得
@router.get("/", response_model=List[schemas.OceanDataResponse])
def read_ocean_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_ocean_data(db, skip=skip, limit=limit)

# 指定した期間内の海洋データを取得
@router.get("/range/", response_model=List[schemas.OceanDataResponse])
def read_ocean_data_by_range(start: datetime, end: datetime, db: Session = Depends(get_db)):
    return crud.get_ocean_data_by_time_range(db, start_time=start, end_time=end)
