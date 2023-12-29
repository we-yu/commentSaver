from pydantic import BaseModel, HttpUrl, validator, conint
from typing import Optional
from datetime import datetime

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

    @validator('article_id', 'last_res_id')
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

class ArticleDetailCreate(BaseModel):
    article_id: int
    resno: int
    post_name: Optional[str] = None
    post_date: Optional[datetime] = None
    user_id: Optional[str] = None
    bodytext: Optional[str] = None
    page_url: Optional[HttpUrl] = None
    deleted: Optional[bool] = None

    class Config:
        orm_mode = True

class ArticleDetailResponse(BaseModel):
    article_id: int
    resno: int
    post_name: Optional[str] = None
    post_date: Optional[datetime] = None
    user_id: Optional[str] = None
    bodytext: Optional[str] = None
    page_url: Optional[HttpUrl] = None
    deleted: Optional[bool] = None

    class Config:
        orm_mode = True

class ConfigResponse(BaseModel):
    id: int
    category: str
    config_type: str
    value: str

class WebsiteResponse(BaseModel):
    name: str
    url: str
    sub_tag1: str
    sub_tag2: Optional[str] = None  # None を許可する
    sub_tag3: Optional[str] = None  # None を許可する
