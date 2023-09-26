from models import db_models
from sqlalchemy.orm import Session
from sqlalchemy import func

def get_article_by_name(db: Session, name: str):
    return db.query(db_models.ArticleList).filter(func.lower(db_models.ArticleList.title) == func.lower(name)).first()

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

def create_article(db: Session, article: db_models.ArticleList):

    db.add(article)
    db.commit()
    db.refresh(article)
    return article

# 他のCRUD処理
