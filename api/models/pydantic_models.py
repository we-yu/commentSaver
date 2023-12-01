from pydantic import BaseModel, HttpUrl, validator, conint
from typing import Optional

class ArticleListResponse(BaseModel):
    article_id: int
    title: str
    url: str
    last_res_id: int
    moved: bool
    new_id: int

class ArticleListCreate(BaseModel):
    article_id: int
    title: str
    url: HttpUrl
    last_res_id: int
    moved: bool
    new_id: int

    @validator('article_id', 'title', 'last_res_id', 'moved', 'new_id')
    def must_not_be_none(cls, v):
        if v is None:
            raise ValueError('must not be None')
        return v

    @validator('article_id', 'last_res_id', 'new_id')
    def must_be_positive(cls, v):
        if v < 0:
            raise ValueError('must be positive')
        return v

# 他のPydanticモデルもここに

# 更新用(UPDATE)のモデル
class ArticleListUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[HttpUrl] = None
    last_res_id: Optional[int] = None
    moved: Optional[bool] = None
    new_id: Optional[int] = None

