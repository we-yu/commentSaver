from fastapi import FastAPI
from routers.api_router import router  # ルータのインポート

app = FastAPI()

app.include_router(router)  # ルータをインクルード
