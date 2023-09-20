from models import db_models
from sqlalchemy.orm import Session
from sqlalchemy import func

def get_article_by_name(db: Session, name: str):
    return db.query(db_models.ArticleList).filter(func.lower(db_models.ArticleList.title) == func.lower(name)).first()

def create_article(db: Session, article: db_models.ArticleList):

    db.add(article)
    db.commit()
    db.refresh(article)
    return article

# 他のCRUD処理
