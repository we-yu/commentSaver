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
def find_article_list(
    db: Session,
    article_id: Optional[int] = None,
    title: Optional[str] = None,
    ):
    if article_id:
        db_article = db.query(db_models.ArticleList).filter(db_models.ArticleList.article_id == article_id).first()
    elif title:
        db_article = db.query(db_models.ArticleList).filter(func.lower(db_models.ArticleList.title) == func.lower(title)).first()
    
    if db_article:
        # 属性を辞書として返す
        return {
            "article_id": db_article.article_id,
            "title": db_article.title,
            "url": db_article.url,
            "last_res_id": db_article.last_res_id,
            "moved": db_article.moved,
            "new_id": db_article.new_id,
        }

# Article_listテーブルに、新しい記事を追加する(INSERT)
def insert_article_list(
    db: Session,
    article_id: int,
    title: str,
    url: str,
    last_res_id: int,
    moved: bool,
    new_id: int,
    ):

    # Validation
    # 既存のarticle_idと重複していないかチェック
    existing_article = db.query(db_models.ArticleList).filter(db_models.ArticleList.article_id == article_id).first()
    if existing_article:
        # 重複している場合はNoneを返して終了
        return None


    # 新しいインスタンスを作成
    new_article_record = db_models.ArticleList(
        article_id=article_id,
        title=title,
        url=url,
        last_res_id=last_res_id,
        moved=moved,
        new_id=new_id,
    )

    # セッションに追加
    db.add(new_article_record)

    # 変更をコミット
    db.commit()

    # 変更を反映
    db.refresh(new_article_record)

    # 属性を辞書として返す
    return {
        "article_id": new_article_record.article_id,
        "title": new_article_record.title,
        "url": new_article_record.url,
        "last_res_id": new_article_record.last_res_id,
        "moved": new_article_record.moved,
        "new_id": new_article_record.new_id,
    }

# 他のCRUD処理

# Article_listテーブルのレコードを更新する(UPDATE)
def update_article_list(
    db: Session,
    article_id: int,
    title: Optional[str] = None,
    url: Optional[str] = None,
    last_res_id: Optional[int] = None,
    moved: Optional[bool] = None,
    new_id: Optional[int] = None,
):
    # 既存の記事を取得
    db_article = db.query(db_models.ArticleList).filter(db_models.ArticleList.article_id == article_id).first()

    # 記事が存在しない場合はNoneを返して終了
    if db_article is None:
        return None

    # 記事が存在する場合は、提供された値で記事を更新（Noneでない場合のみ更新）
    if title is not None: db_article.title = title
    if url is not None: db_article.url = url
    if last_res_id is not None: db_article.last_res_id = last_res_id
    if moved is not None: db_article.moved = moved
    if new_id is not None: db_article.new_id = new_id

    # 変更をコミット
    db.commit()

    # 変更を反映
    db.refresh(db_article)

    # 属性を辞書として返す
    return {
        "article_id": db_article.article_id,
        "title": db_article.title,
        "url": db_article.url,
        "last_res_id": db_article.last_res_id,
        "moved": db_article.moved,
        "new_id": db_article.new_id,
    }


# Article_listテーブルのレコードを削除する(DELETE)
def delete_article_list(db: Session, article_id: int):
    db_article = db.query(db_models.ArticleList).filter(db_models.ArticleList.article_id == article_id).first()
    if db_article:
        # 属性を辞書として保存
        article_data = {
            "article_id": db_article.article_id,
            "title": db_article.title,
            "url": db_article.url,
            "last_res_id": db_article.last_res_id,
            "moved": db_article.moved,
            "new_id": db_article.new_id,
        }

        # 記事の削除
        db.delete(db_article)
        db.commit()

        # 削除された記事のデータを返す
        return article_data
    return None
