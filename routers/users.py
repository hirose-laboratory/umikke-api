from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import crud, schemas
from database import get_db

router = APIRouter(prefix="/users", tags=["Users & Groups"])

# ================================
# 新規追加: ユーザー登録API (POST)
# ================================
@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 既に同じメールアドレスが登録されていないかチェック
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 問題なければ作成処理を呼び出す
    return crud.create_user(db=db, user=user)

@router.delete("/delete")
def delete_user(user: UserDelete, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    # crud.pyにdelete_user関数を実装している前提です
    crud.delete_user(db=db, user_id=db_user.id)
    return {"message": "Account deleted successfully"}

# ================================
# 既存のAPI (GET)
# ================================



@router.get("/", response_model=List[schemas.UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

@router.get("/group/{group_id}", response_model=List[schemas.UserResponse])
def read_users_by_group(group_id: int, db: Session = Depends(get_db)):
    return crud.get_users_by_group(db, group_id=group_id)

@router.get("/groups/", response_model=List[schemas.GroupResponse])
def read_groups(db: Session = Depends(get_db)):
    return crud.get_groups(db)

@router.post("/login")
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    # 1. ユーザーが存在するかチェック
    db_user = crud.get_user_by_email(db, email=user_credentials.email)
    if not db_user:
        # ★ エラー詳細を分かりやすく変更
        raise HTTPException(status_code=400, detail="エラー: このメールアドレスは登録されていません")
    
    # 2. パスワードが一致するかチェック
    if not crud.verify_password(user_credentials.password, db_user.password_hash):
        # ★ エラー詳細を分かりやすく変更
        raise HTTPException(status_code=400, detail="エラー: パスワードが間違っています")
    
    return {
        "message": "Login successful",
        "token": "dummy_access_token_12345",
        "email": db_user.email
    }
