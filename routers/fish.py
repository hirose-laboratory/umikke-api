from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import crud, schemas
from database import get_db

router = APIRouter(prefix="/fish", tags=["Fish & eDNA & Hotpoints"])

@router.get("/", response_model=List[schemas.FishDataResponse])
def read_fish(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_fish_data(db, skip=skip, limit=limit)

@router.get("/search/", response_model=List[schemas.FishDataResponse])
def search_fish(name: str, db: Session = Depends(get_db)):
    return crud.get_fish_by_name(db, name=name)

@router.get("/{fish_id}/edna", response_model=List[schemas.EDNAActualResponse])
def read_edna_by_fish(fish_id: int, db: Session = Depends(get_db)):
    return crud.get_edna_actual_by_fish(db, fish_id=fish_id)

@router.get("/hotpoints/high-score", response_model=List[schemas.HotpointResponse])
def read_hotpoints(min_score: float = 0.5, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_hotpoints_above_score(db, min_score=min_score, limit=limit)

@router.get("/{fish_id}/suggestions", response_model=List[schemas.SuggestResponse])
def read_suggestions_by_fish(fish_id: int, db: Session = Depends(get_db)):
    return crud.get_suggestions_by_fish(db, fish_id=fish_id)

@router.get("/{fish_id}/edna-prediction", response_model=List[schemas.EDNAPredictionResponse])
def read_edna_prediction_by_fish(fish_id: int, db: Session = Depends(get_db)):
    return crud.get_edna_prediction_by_fish(db, fish_id=fish_id)
