from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # ← ★これが不足していたためNameErrorになっていました
from routers import users, fish, ocean

app = FastAPI(
    title="umikke System API",
    description="魚の生態、eDNA、海洋データ、およびユーザーを管理・抽出するAPIです。",
    version="1.0.0"
)

# CORSの設定（Next.jsなどの別ポートからの通信を許可する）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発・テスト用。本番環境では特定のURLに絞ることを推奨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 各機能ごとのルーターをマウント
app.include_router(users.router)
app.include_router(fish.router)
app.include_router(ocean.router)

@app.get("/")
def read_root():
    return {"message": "umikke System API is running successfully!"}
