from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import crud, schemas
from database import get_db

router = APIRouter(prefix="/users", tags=["Users & Groups"])

@router.get("/", response_model=List[schemas.UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

@router.get("/group/{group_id}", response_model=List[schemas.UserResponse])
def read_users_by_group(group_id: int, db: Session = Depends(get_db)):
    return crud.get_users_by_group(db, group_id=group_id)

@router.get("/groups/", response_model=List[schemas.GroupResponse])
def read_groups(db: Session = Depends(get_db)):
    return crud.get_groups(db)