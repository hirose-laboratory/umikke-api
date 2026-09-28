# routers/fish.py 

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import crud, schemas
from database import get_db

router = APIRouter(prefix="/fish", tags=["Fish & eDNA & Hotpoints"])

@router.get("/", response_model=List[schemas.FishDataResponse])
def read_fish(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_fish_data(db, skip=skip, limit=limit)

@router.get("/search/", response_model=List[schemas.FishDataResponse])
def search_fish(name: str, db: Session = Depends(get_db)):
    return crud.get_fish_by_name(db, name=name)

# 変更: startとendパラメータを追加
@router.get("/{fish_id}/edna", response_model=List[schemas.EDNAActualResponse])
def read_edna_by_fish(
    fish_id: int, 
    start: Optional[datetime] = None, 
    end: Optional[datetime] = None, 
    db: Session = Depends(get_db)
):
    return crud.get_edna_actual_by_fish(db, fish_id=fish_id, start_time=start, end_time=end)

# 変更: startとendパラメータを追加
@router.get("/hotpoints/high-score", response_model=List[schemas.HotpointResponse])
def read_hotpoints(
    min_score: float = 0.5, 
    limit: int = 50, 
    start: Optional[datetime] = None, 
    end: Optional[datetime] = None, 
    db: Session = Depends(get_db)
):
    return crud.get_hotpoints_above_score(db, min_score=min_score, limit=limit, start_time=start, end_time=end)

@router.get("/{fish_id}/suggestions", response_model=List[schemas.SuggestResponse])
def read_suggestions_by_fish(fish_id: int, db: Session = Depends(get_db)):
    return crud.get_suggestions_by_fish(db, fish_id=fish_id)

# 変更: startとendパラメータを追加
@router.get("/{fish_id}/edna-prediction", response_model=List[schemas.EDNAPredictionResponse])
def read_edna_prediction_by_fish(
    fish_id: int, 
    start: Optional[datetime] = None, 
    end: Optional[datetime] = None, 
    db: Session = Depends(get_db)
):
    return crud.get_edna_prediction_by_fish(db, fish_id=fish_id, start_time=start, end_time=end)
