from models import db_models
from models.db_models import Website, Config
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from models.pydantic_models import ArticleDetailCreate, ArticleDetailResponse, WebsiteResponse

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
            "article_id": db_article.article_id,  # 必要なら属性名を変更してください
            "title": db_article.title,
            "url": db_article.url,
            "last_res_id": db_article.last_res_id,
            "moved": db_article.moved,
            "new_article_title": db_article.new_article_title
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
            "new_article_title": db_article.new_article_title,
        }

# Article_listテーブルに、新しい記事を追加する(INSERT)
def create_article_list(
    db: Session,
    article_id: int,
    title: str,
    url: str,
    last_res_id: int,
    moved: bool,
    new_article_title: str,
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
        new_article_title=new_article_title,
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
        "new_article_title": new_article_record.new_article_title,
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
    new_article_title: Optional[str] = None,
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
    if new_article_title is not None: db_article.new_article_title = new_article_title

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
        "new_article_title": db_article.new_article_title,
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
            "new_article_title": db_article.new_article_title,
        }

        # 記事の削除
        db.delete(db_article)
        db.commit()

        # 削除された記事のデータを返す
        return article_data
    return None

# Article_detailテーブルのレコードを追加する(INSERT)
def insert_article_details(db: Session, article_details: List[ArticleDetailCreate]):
    # Pydantic モデルから SQLAlchemy モデルへの変換
    db_article_details = [db_models.ArticleDetail(**detail.dict()) for detail in article_details]

    db.add_all(db_article_details)
    db.commit()

    # SQLAlchemy モデルから Pydantic モデルへの変換
    return [ArticleDetailCreate.from_orm(detail) for detail in db_article_details]

# Article_detailテーブルのレコードを取得する(READ)
def get_article_details(db: Session, article_id: int) -> List[ArticleDetailResponse]:
    details = db.query(db_models.ArticleDetail).filter(db_models.ArticleDetail.article_id == article_id).all()
    return [ArticleDetailResponse.from_orm(detail) for detail in details]

def read_config_by_type(db: Session, config_type: str):
    return db.query(Config).filter(Config.config_type == config_type).first()

def get_website_by_name(db: Session, name: str) -> WebsiteResponse:
    db_website = db.query(Website).filter(Website.name == name).first()
    if db_website:
        # SQLAlchemy オブジェクトを Pydantic モデルに変換
        return WebsiteResponse.from_orm(db_website)
    return None

def create_website(db: Session, website_data):
    db_website = Website(**website_data)
    db.add(db_website)
    db.commit()
    db.refresh(db_website)
    return db_website

