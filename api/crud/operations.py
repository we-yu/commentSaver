from models import db_models
from sqlalchemy.orm import Session

def create_article(db: Session, article: db_models.ArticleList):

    db.add(article)
    db.commit()
    db.refresh(article)
    return article

# 他のCRUD処理
