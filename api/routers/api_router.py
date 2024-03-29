import os

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from crud import operations
from typing import List, Union, Optional
from models import pydantic_models, db_models
from models.pydantic_models import ArticleListResponse, ArticleListCreate, ArticleListUpdate, ArticleDetailCreate, ArticleDetailResponse, ConfigResponse, WebsiteResponse
from sqlalchemy.exc import OperationalError
from session_manager import SessionManager

import httpx

# load_dotenv('../../.env') # 環境変数のロード
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")

# SQLAlchemyの設定（
DATABASE_URL = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@db_container/{MYSQL_DATABASE}'
engine = create_engine(DATABASE_URL)

session_manager = SessionManager(DATABASE_URL)

# 依存性
def get_db():
    with session_manager.session() as db:
        yield db

router = APIRouter()

# @router.post("/article/")
# def create_article(article: pydantic_models.ArticleListCreate, db: Session = Depends(get_db)):
#     db_article = db_models.Article(**article.dict())
#     return operations.create_article(db, db_article)

# 以下、デバッグ用のコード
@router.get("/hello")
def hello():
    return {"message": "Hello, world!"}

@router.get("/db-test")
def test_db_connection(db: Session = Depends(get_db)):
    try:
        # シンプルなSQLクエリを実行して接続をテスト
        db.execute("SELECT 1")
        return {"status": "ok", "message": "Database connection successful"}
    except OperationalError:
        return {"status": "error", "message": "Database connection failed"}

# Scraper用のエンドポイント --------------------------------------------------

# CRUD処理 for article_list --------------------------------------------------
# CREATE:記事一覧情報を追加する
@router.post("/article_list", response_model=ArticleListResponse)
def create_article_list(article: ArticleListCreate, db: Session = Depends(get_db)):

    # PandanticモデルをDBモデルに変換
    article_dict = article.dict()

    print("article_dict =", article_dict)

    # article_listテーブルにレコードを追加
    db_article = operations.create_article_list(db, **article_dict)

    # Noneが返ってきた場合は、400エラーを返す
    if db_article is None:
        raise HTTPException(status_code=400, detail="Same article ID already exists")

    # DBモデルをPandanticモデルに変換
    res_article = ArticleListResponse(**db_article)

    return res_article

# READ:記事一覧情報を取得する
@router.get("/article_list", response_model=Union[List[ArticleListResponse], ArticleListResponse])
async def read_all_article_lists(
        article_id: Optional[int] = Query(None, description="記事ID", ge=1),  # Optionalを使っている
        title: str = Query(None, description="記事タイトル", min_length=1, max_length=255),
        db: Session = Depends(get_db)
    ):
    # article_idまたはtitleが指定されている場合
    if article_id or title:
        # 指定された条件で記事を取得
        db_article = operations.find_article_list(db, article_id, title)

        print("db_article =", db_article)

        # 記事が取得できた場合は、レスポンスモデルに変換して返す
        # 取得項目を追加する場合は、models/pydantic_models.pyのArticleListResponseの定義を変更してください
        if db_article:
            return ArticleListResponse(**db_article)
        # 記事が取得できなかった場合は、404エラーを返す
        else:
            raise HTTPException(status_code=404, detail="Article not found")
    else: # IDまたはタイトルが指定されていない場合
        articles = operations.get_all_articles(db)
        return [ArticleListResponse(**article) for article in articles]

        # articles = operations.get_all_articles(db)
        # return articles

@router.get("/article_list/all", response_model=List[ArticleListResponse])
def read_all_articles(db: Session = Depends(get_db)):
    articles = operations.get_all_articles(db)
    return [ArticleListResponse(**article) for article in articles]

# UPDATE:記事一覧情報を更新する
@router.put("/article_list/{article_id}", response_model=ArticleListResponse)
def update_article_list(article_id: int, article: ArticleListUpdate, db: Session = Depends(get_db)):

    # PandanticモデルをDBモデルに変換
    article_dict = article.dict(exclude_unset=True)

    # article_listテーブルのレコードを更新
    db_article = operations.update_article_list(db, article_id, **article_dict)

    # Noneが返ってきた場合は、404エラーを返す
    if db_article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    # DBモデルをPandanticモデルに変換
    res_article = ArticleListResponse(**db_article)

    return res_article


# DELETE:記事一覧情報を削除する
@router.delete("/article_list/{article_id}", response_model=ArticleListResponse)
def delete_article_list(article_id: int, db: Session = Depends(get_db)):
    db_article = operations.delete_article_list(db, article_id)
    if db_article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return db_article

# CRUD処理 for article_detail --------------------------------------------------

# CREATE:記事詳細情報を追加する
@router.post("/article_details", response_model=List[ArticleDetailCreate])
def create_article_details(article_details: List[ArticleDetailCreate], db: Session = Depends(get_db)):
    try:
        created_details = operations.insert_article_details(db, article_details)
        return created_details
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# READ:記事詳細情報を取得する
@router.get("/article_details/{article_id}", response_model=List[ArticleDetailResponse])
def get_article_details(article_id: int, db: Session = Depends(get_db)):
    details = operations.get_article_details(db, article_id)
    if not details:
        raise HTTPException(status_code=404, detail="Article details not found")
    return details

@router.get("/config/{config_type}", response_model=ConfigResponse)
async def read_config_by_type(config_type: str, db: Session = Depends(get_db)):
    db_config = operations.read_config_by_type(db, config_type)
    if db_config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    
    # db_config オブジェクトを ConfigResponse モデルに変換
    config_response = ConfigResponse(
        id=db_config.id,
        category=db_config.category,
        config_type=db_config.config_type,
        value=db_config.value
    )
    return config_response

@router.get("/websites/{name}", response_model=WebsiteResponse)
def get_website(name: str, db: Session = Depends(get_db)):
    website_response = operations.get_website_by_name(db, name)
    if website_response is None:
        raise HTTPException(status_code=404, detail="Website not found")
    return website_response

# セッション管理 --------------------------------------------------
# セッション管理
@router.post("/session/create")
def create_session():
    db_session = session_manager.create_session()
    return {"session_id": id(db_session)}

@router.delete("/session/{session_id}")
def close_session(session_id: int):
    session_manager.close_session(session_id)

# トランザクション管理
@router.post("/transaction/{session_id}/{action}")
def manage_transaction(session_id: int, action: str):
    if action == "begin":
        session_manager.begin_transaction(session_id)
    elif action == "commit":
        session_manager.commit_transaction(session_id)
    elif action == "rollback":
        session_manager.rollback_transaction(session_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


# WebAPP用のエンドポイント --------------------------------------------------
@router.get("/forward-to-scraper/{article_title}")
async def forward_to_scraper(article_title: str):
    print("article_title =", article_title)
    scraper_url = f"http://scraper_container:8000/process-article/{article_title}"
    async with httpx.AsyncClient() as client:
        response = await client.get(scraper_url)
        response.raise_for_status()
        return response.json()
