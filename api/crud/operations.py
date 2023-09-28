from models import db_models
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

def get_article_by_name(db: Session, name: str):
    return db.query(db_models.ArticleList).filter(func.lower(db_models.ArticleList.title) == func.lower(name)).first()

# Article_listテーブルの全レコードを取得する
def get_all_articles(db: Session):
    # query DB for all articles
    db_articles = db.query(db_models.ArticleList).all()
    
    # convert each ArticleList instance to a dictionary
    articles = []
    for db_article in db_articles:
        article = {
            "article_id": db_article.article_id,  # もしこの属性名が違う場合は、適切な属性名に変更してください
            "title": db_article.title,
            "url": db_article.url
        }
        articles.append(article)
    
    return articles

# Article_listテーブルから、指定された条件(ID or Title)で記事を取得する
def get_article_by_id_or_title(db: Session, article_id: Optional[int] = None, title: Optional[str] = None):
    if article_id:
        return db.query(db_models.ArticleList).filter(db_models.ArticleList.article_id == article_id).first()
    elif title:
        return db.query(db_models.ArticleList).filter(func.lower(db_models.ArticleList.title) == func.lower(title)).first()

def create_article(db: Session, article: db_models.ArticleList):

    db.add(article)
    db.commit()
    db.refresh(article)
    return article

# 他のCRUD処理