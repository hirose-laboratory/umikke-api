import os
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# 環境変数からデータベースURLを取得
DATABASE_URL = os.getenv("DATABASE_URL")

# データベース接続の設定
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# テーブルのモデル定義（実際の umikke DB 内のテーブル名・カラムに合わせます）
class TargetTable(Base):
    __tablename__ = "your_table_name"  # 作成したテーブル名に変更してください
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, index=True)  # 例: グループID
    data_value = Column(String(255))        # 例: 保存されているデータ

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "umikke DB API is running"}

@app.get("/data/{group_id}")
def get_data_by_group(group_id: int):
    db = SessionLocal()
    try:
        # 指定された group_id のデータを取得
        results = db.query(TargetTable).filter(TargetTable.group_id == group_id).all()
        if not results:
            raise HTTPException(status_code=404, detail="Data not found")
        
        return {"group_id": group_id, "data": results}
    finally:
        db.close()