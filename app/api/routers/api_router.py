from fastapi import APIRouter
from ..dependencies import handle_article_entry

router = APIRouter()

# 例: テストエンドポイント
@router.get("/test")
async def test_endpoint():
    return {"message": "This is a test endpoint"}

@router.get("/process-article/{title}")
async def process_article_endpoint(title: str):
    # 非同期関数 api_entrypoint を await で呼び出す
    response = await handle_article_entry(title)

    # result_message = str(response.status_code) + ": " + message

    return response.status_code

# CRUD操作やデータベースとの連携など、具体的な実装はプロジェクトの要件に応じて行う
