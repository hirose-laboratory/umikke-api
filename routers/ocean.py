from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import crud, schemas
from database import get_db

router = APIRouter(prefix="/ocean", tags=["Ocean Data"])

@router.get("/", response_model=List[schemas.OceanDataResponse])
def read_ocean_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_ocean_data(db, skip=skip, limit=limit)

@router.get("/range/", response_model=List[schemas.OceanDataResponse])
def read_ocean_data_by_range(start: datetime, end: datetime, db: Session = Depends(get_db)):
    """例: /ocean/range/?start=2023-01-01T00:00:00&end=2023-12-31T23:59:59"""
    return crud.get_ocean_data_by_time_range(db, start_time=start, end_time=end)