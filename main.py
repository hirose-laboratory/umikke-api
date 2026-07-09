from fastapi import FastAPI
from routers import users, fish, ocean

app = FastAPI(
    title="umikke System API",
    description="魚の生態、eDNA、海洋データ、およびユーザーを管理・抽出するAPIです。",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # テスト用。本番では ["http://27.133.132.208:3000"] に絞るのを推奨
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
