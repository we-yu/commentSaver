from pydantic import BaseModel

class ArticleResponse(BaseModel):
    article_id: int
    title: str
    url: str

class ArticleListCreate(BaseModel):
    article_id: int
    title: str
    # ...他のフィールド

# 他のPydanticモデルもここに
