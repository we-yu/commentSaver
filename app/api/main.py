# /app/api/main.py
from fastapi import FastAPI
from .routers.api_router import router  # APIコンテナと同じルーターを使用

app = FastAPI()

app.include_router(router)  # ルータをインクルード
