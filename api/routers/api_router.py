from fastapi import APIRouter, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from crud import operations
from models import pydantic_models, db_models

# SQLAlchemyの設定（URLは適切なものに置き換えてください）
DATABASE_URL = "sqlite:///./test.db"
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

@router.post("/article/")
def create_article(article: pydantic_models.ArticleListCreate, db: Session = Depends(get_db)):
    db_article = db_models.Article(**article.dict())
    return operations.create_article(db, db_article)

@router.get("/hello/")
def hello():
    return {"message": "Hello, world!"}
