from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.api_router import router  # ルータのインポート

app = FastAPI()

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのオリジンを許可
    allow_credentials=True,
    allow_methods=["*"],  # すべてのHTTPメソッドを許可
    allow_headers=["*"],  # すべてのHTTPヘッダーを許可
)

app.include_router(router)  # ルータをインクルード
