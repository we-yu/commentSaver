from pydantic import BaseModel

class ArticleResponse(BaseModel):
    article_id: int
    title: str
    url: str
    last_res_id: int
    moved: bool
    new_id: int

class ArticleListCreate(BaseModel):
    article_id: int
    title: str
    # ...他のフィールド

# 他のPydanticモデルもここに
