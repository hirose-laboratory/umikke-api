# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import crud, schemas
from database import get_db

router = APIRouter(prefix="/users", tags=["Users & Groups"])

# ユーザー登録
@router.post("/register", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 同一メールアドレスの重複登録を防止
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

# ユーザーアカウントの削除
@router.delete("/delete")
def delete_user(user: schemas.UserDelete, db: Session = Depends(get_db)):
    # 削除対象のユーザーが存在するか確認
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    crud.delete_user(db=db, user_id=db_user.id)
    return {"message": "Account deleted successfully"}

# ユーザー情報を一覧取得（ページネーション対応）
@router.get("/", response_model=List[schemas.UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

# 特定のグループに所属するユーザーを取得
@router.get("/group/{group_id}", response_model=List[schemas.UserResponse])
def read_users_by_group(group_id: int, db: Session = Depends(get_db)):
    return crud.get_users_by_group(db, group_id=group_id)

# 登録されているグループ情報を一覧取得
@router.get("/groups/", response_model=List[schemas.GroupResponse])
def read_groups(db: Session = Depends(get_db)):
    return crud.get_groups(db)

# ユーザーログイン処理
@router.post("/login")
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    # アカウントの存在確認
    db_user = crud.get_user_by_email(db, email=user_credentials.email)
    if not db_user:
        raise HTTPException(status_code=400, detail="エラー: このメールアドレスは登録されていません")
    
    # パスワードの照合
    if not crud.verify_password(user_credentials.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="エラー: パスワードが間違っています")
    
    return {
        "message": "Login successful",
        "token": "dummy_access_token_12345",
        "email": db_user.email
    }
