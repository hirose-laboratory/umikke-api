from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import users, fish, ocean

app = FastAPI(
    title="umikke System API",
    description="apiテスト",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://27.133.132.208:3000"], 
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
