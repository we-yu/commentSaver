import os

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from crud import operations
from typing import List, Union, Optional
from models import pydantic_models, db_models
from models.pydantic_models import ArticleResponse
from sqlalchemy.exc import OperationalError

# load_dotenv('../../.env') # 環境変数のロード
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")

# SQLAlchemyの設定（URLは適切なものに置き換えてください）
DATABASE_URL = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@db_container/{MYSQL_DATABASE}'
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 依存性
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

# 記事一覧情報を取得する
@router.get("/article_list", response_model=Union[List[ArticleResponse], ArticleResponse])
async def get_all_articles(
        article_id: Optional[int] = Query(None, description="記事ID", ge=1),  # Optionalを使っている
        title: str = Query(None, description="記事タイトル", min_length=1, max_length=255),
        db: Session = Depends(get_db)
    ):
    # article_idまたはtitleが指定されている場合
    if article_id or title:
        # 指定された条件で記事を取得
        db_article = operations.get_article_by_id_or_title(db, article_id, title)

        # 記事が取得できた場合は、レスポンスモデルに変換して返す
        if db_article:
            return ArticleResponse(**db_article)
        # 記事が取得できなかった場合は、404エラーを返す
        else:
            raise HTTPException(status_code=404, detail="Article not found")
    else: # IDまたはタイトルが指定されていない場合
        articles = operations.get_all_articles(db)
        return [ArticleResponse(**article) for article in articles]

        # articles = operations.get_all_articles(db)
        # return articles


@router.get("/articles")
# def get_article_by_name(name: str, db: Session = Depends(get_db)):
#     db_article = operations.get_article_by_name(db, name)
def read_articles(name: str = Query(..., min_length=2, max_length=255)):
    if name.lower() == 'ubuntu':
        return {
            "article": {
                "article_id": 123,
                "title": "Ubuntu",
                "url": "http://example.com/ubuntu-article",
                "last_res_id": 456
            }
        }
    else:
        return {"message": "Article not found"}    

