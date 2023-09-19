from pydantic import BaseModel

class ArticleListCreate(BaseModel):
    article_id: int
    title: str
    # ...他のフィールド

# 他のPydanticモデルもここに
